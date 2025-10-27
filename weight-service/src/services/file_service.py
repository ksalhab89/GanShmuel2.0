"""File processing service for CSV/JSON container data uploads."""

import csv
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.schemas import BatchUploadResponse, ContainerWeightData
from ..utils.calculations import normalize_weight_to_kg, validate_weight_range
from .container_service import ContainerService


class FileProcessingError(Exception):
    """Exception raised for file processing errors."""
    pass


class FileValidationError(Exception):
    """Exception raised for file validation errors."""
    pass


class FileService:
    """File processing service for batch container data uploads."""
    
    def __init__(self, session: AsyncSession, upload_dir: Optional[str] = None):
        self.session = session
        self.container_service = ContainerService(session)
        self.upload_dir = upload_dir or "/in"
        
        # Ensure upload directory exists
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
    
    async def process_batch_file(self, 
                               filename: str,
                               allow_updates: bool = True,
                               skip_duplicates: bool = False) -> BatchUploadResponse:
        """
        Main file processing entry point.
        
        Args:
            filename: Name of the uploaded file
            allow_updates: Whether to allow updating existing containers
            skip_duplicates: Whether to skip duplicate containers
            
        Returns:
            BatchUploadResponse with processing results
            
        Raises:
            FileProcessingError: File processing failed
            FileValidationError: File validation failed
        """
        file_path = os.path.join(self.upload_dir, filename)
        
        # Validate file existence and format
        self._validate_file_format(file_path)
        
        try:
            # Parse file based on extension
            if filename.lower().endswith('.csv'):
                container_data = await self._parse_csv_file(file_path)
            elif filename.lower().endswith('.json'):
                container_data = await self._parse_json_file(file_path)
            else:
                raise FileValidationError(f"Unsupported file format: {filename}")
            
            # Process containers in batch
            results = await self.container_service.batch_register_containers(
                container_data,
                allow_updates=allow_updates,
                skip_duplicates=skip_duplicates
            )
            
            # Format response
            return BatchUploadResponse(
                message=self._format_batch_message(results),
                processed_count=results["processed"] + results["updated"],
                skipped_count=results["skipped"],
                errors=results["errors"]
            )
            
        except Exception as e:
            raise FileProcessingError(f"Failed to process file {filename}: {str(e)}")
    
    async def _parse_csv_file(self, file_path: str) -> List[ContainerWeightData]:
        """
        Parse CSV file containing container data.
        
        Supported formats:
        - id,kg
        - id,lbs
        - container_id,weight,unit (with header)
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of ContainerWeightData objects
            
        Raises:
            FileProcessingError: CSV parsing failed
        """
        container_data = []
        errors = []
        
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                # Try to detect if file has headers
                sample = csvfile.read(1024)
                csvfile.seek(0)
                
                # Check if first line looks like headers
                first_line = csvfile.readline().strip()
                csvfile.seek(0)
                
                has_header = any(keyword in first_line.lower() for keyword in ['id', 'weight', 'container'])
                
                reader = csv.reader(csvfile)
                
                if has_header:
                    # Skip header row
                    header = next(reader, None)
                    if not header:
                        raise FileProcessingError("Empty CSV file")
                
                row_num = 1 if has_header else 0
                
                for row in reader:
                    row_num += 1
                    
                    try:
                        # Skip empty rows
                        if not row or all(not cell.strip() for cell in row):
                            continue
                        
                        # Parse row based on number of columns
                        if len(row) == 2:
                            # Format: id,weight (assume kg unless weight suggests lbs)
                            container_id = row[0].strip()
                            weight_str = row[1].strip()
                            
                            if not container_id:
                                errors.append(f"Row {row_num}: Empty container ID")
                                continue
                            
                            try:
                                weight = int(float(weight_str))
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid weight '{weight_str}'")
                                continue
                            
                            # Auto-detect unit based on weight range
                            unit = "lbs" if weight > 500 else "kg"  # Heuristic for common container weights
                            
                        elif len(row) == 3:
                            # Format: id,weight,unit
                            container_id = row[0].strip()
                            weight_str = row[1].strip()
                            unit = row[2].strip().lower()
                            
                            if not container_id:
                                errors.append(f"Row {row_num}: Empty container ID")
                                continue
                            
                            try:
                                weight = int(float(weight_str))
                            except ValueError:
                                errors.append(f"Row {row_num}: Invalid weight '{weight_str}'")
                                continue
                            
                            if unit not in ['kg', 'lbs']:
                                errors.append(f"Row {row_num}: Invalid unit '{unit}'. Must be 'kg' or 'lbs'")
                                continue
                        
                        else:
                            errors.append(f"Row {row_num}: Invalid number of columns ({len(row)}). Expected 2 or 3")
                            continue
                        
                        # Validate container data
                        try:
                            self._validate_csv_container_data(container_id, weight, unit)
                            
                            container_data.append(ContainerWeightData(
                                id=container_id,
                                weight=weight,
                                unit=unit
                            ))
                            
                        except Exception as e:
                            errors.append(f"Row {row_num}: {str(e)}")
                    
                    except Exception as e:
                        errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
                
                if errors:
                    # If we have some valid data, continue with warnings
                    if container_data:
                        print(f"Warning: {len(errors)} errors found in CSV file, processing {len(container_data)} valid rows")
                    else:
                        raise FileProcessingError(f"No valid data found. Errors: {'; '.join(errors[:5])}")
                
                return container_data
                
        except FileNotFoundError:
            raise FileProcessingError(f"CSV file not found: {file_path}")
        except Exception as e:
            raise FileProcessingError(f"Failed to parse CSV file: {str(e)}")
    
    async def _parse_json_file(self, file_path: str) -> List[ContainerWeightData]:
        """
        Parse JSON file containing container data.
        
        Expected format:
        [
            {"id": "C001", "weight": 50, "unit": "kg"},
            {"id": "C002", "weight": 110, "unit": "lbs"}
        ]
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            List of ContainerWeightData objects
            
        Raises:
            FileProcessingError: JSON parsing failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as jsonfile:
                data = json.load(jsonfile)
            
            if not isinstance(data, list):
                raise FileProcessingError("JSON must contain an array of container objects")
            
            container_data = []
            errors = []
            
            for i, item in enumerate(data):
                try:
                    # Validate JSON structure
                    if not isinstance(item, dict):
                        errors.append(f"Item {i+1}: Must be an object")
                        continue
                    
                    # Required fields
                    if 'id' not in item:
                        errors.append(f"Item {i+1}: Missing 'id' field")
                        continue
                    
                    if 'weight' not in item:
                        errors.append(f"Item {i+1}: Missing 'weight' field")
                        continue
                    
                    container_id = str(item['id']).strip()
                    
                    # Parse weight
                    try:
                        weight = int(item['weight'])
                    except (ValueError, TypeError):
                        errors.append(f"Item {i+1}: Invalid weight '{item['weight']}'")
                        continue
                    
                    # Parse unit (default to kg)
                    unit = str(item.get('unit', 'kg')).lower().strip()
                    if unit not in ['kg', 'lbs']:
                        errors.append(f"Item {i+1}: Invalid unit '{unit}'. Must be 'kg' or 'lbs'")
                        continue
                    
                    # Validate container data
                    try:
                        self._validate_json_container_data(container_id, weight, unit)
                        
                        container_data.append(ContainerWeightData(
                            id=container_id,
                            weight=weight,
                            unit=unit
                        ))
                        
                    except Exception as e:
                        errors.append(f"Item {i+1}: {str(e)}")
                
                except Exception as e:
                    errors.append(f"Item {i+1}: Unexpected error - {str(e)}")
            
            if errors:
                if container_data:
                    print(f"Warning: {len(errors)} errors found in JSON file, processing {len(container_data)} valid items")
                else:
                    raise FileProcessingError(f"No valid data found. Errors: {'; '.join(errors[:5])}")
            
            return container_data
            
        except FileNotFoundError:
            raise FileProcessingError(f"JSON file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise FileProcessingError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise FileProcessingError(f"Failed to parse JSON file: {str(e)}")
    
    def _validate_file_format(self, file_path: str) -> None:
        """
        Validate file format and accessibility.
        
        Args:
            file_path: Path to file
            
        Raises:
            FileValidationError: File validation failed
        """
        # Check file existence
        if not os.path.exists(file_path):
            raise FileValidationError(f"File not found: {file_path}")
        
        # Check file is readable
        if not os.access(file_path, os.R_OK):
            raise FileValidationError(f"File not readable: {file_path}")
        
        # Check file size (max 10MB)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise FileValidationError(f"File too large: {file_size} bytes (max 10MB)")
        
        # Check file extension
        filename = os.path.basename(file_path)
        if not (filename.lower().endswith('.csv') or filename.lower().endswith('.json')):
            raise FileValidationError(f"Invalid file format. Must be .csv or .json")
        
        # Security check: prevent path traversal
        if '..' in file_path or file_path.startswith('/'):
            if not file_path.startswith(self.upload_dir):
                raise FileValidationError("Invalid file path: security violation")
    
    def _validate_csv_container_data(self, container_id: str, weight: int, unit: str) -> None:
        """
        Validate container data from CSV.
        
        Args:
            container_id: Container identifier
            weight: Container weight
            unit: Weight unit
            
        Raises:
            FileValidationError: Invalid container data
        """
        # Validate container ID
        if not container_id or len(container_id) > 15:
            raise FileValidationError(f"Invalid container ID: '{container_id}'")
        
        if not container_id.replace('-', '').replace('_', '').isalnum():
            raise FileValidationError(f"Container ID contains invalid characters: '{container_id}'")
        
        # Validate weight
        if weight <= 0:
            raise FileValidationError(f"Weight must be positive: {weight}")
        
        if not validate_weight_range(weight, unit):
            raise FileValidationError(f"Weight {weight} {unit} is out of valid range")
    
    def _validate_json_container_data(self, container_id: str, weight: int, unit: str) -> None:
        """
        Validate container data from JSON.
        
        Args:
            container_id: Container identifier
            weight: Container weight
            unit: Weight unit
            
        Raises:
            FileValidationError: Invalid container data
        """
        # Same validation as CSV
        self._validate_csv_container_data(container_id, weight, unit)
    
    def _format_batch_message(self, results: Dict[str, any]) -> str:
        """
        Format batch processing results into message.
        
        Args:
            results: Batch processing results
            
        Returns:
            Formatted message string
        """
        total_processed = results["processed"] + results["updated"]
        
        if results["errors"]:
            return f"Processed {total_processed} containers with {len(results['errors'])} errors"
        elif results["skipped"] > 0:
            return f"Processed {total_processed} containers, skipped {results['skipped']} duplicates"
        else:
            return f"Successfully processed {total_processed} containers"
    
    async def validate_file_content(self, filename: str) -> Dict[str, any]:
        """
        Validate file content without processing.
        
        Args:
            filename: Name of the file to validate
            
        Returns:
            Dictionary with validation results
        """
        file_path = os.path.join(self.upload_dir, filename)
        
        try:
            # Validate file format
            self._validate_file_format(file_path)
            
            # Parse file
            if filename.lower().endswith('.csv'):
                container_data = await self._parse_csv_file(file_path)
            elif filename.lower().endswith('.json'):
                container_data = await self._parse_json_file(file_path)
            else:
                return {
                    "valid": False,
                    "error": f"Unsupported file format: {filename}",
                    "container_count": 0
                }
            
            return {
                "valid": True,
                "container_count": len(container_data),
                "containers": [{"id": c.id, "weight": c.weight, "unit": c.unit} for c in container_data[:10]]  # Preview first 10
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "container_count": 0
            }
    
    async def get_supported_formats(self) -> Dict[str, any]:
        """
        Get information about supported file formats.
        
        Returns:
            Dictionary with format information
        """
        return {
            "csv": {
                "description": "Comma-separated values file",
                "formats": [
                    {"columns": "id,weight", "description": "Container ID and weight (auto-detect unit)"},
                    {"columns": "id,weight,unit", "description": "Container ID, weight, and unit (kg/lbs)"}
                ],
                "example": "C001,50,kg\nC002,110,lbs"
            },
            "json": {
                "description": "JavaScript Object Notation file",
                "format": "Array of objects with id, weight, and unit fields",
                "example": '[{"id":"C001","weight":50,"unit":"kg"},{"id":"C002","weight":110,"unit":"lbs"}]'
            },
            "limits": {
                "max_file_size": "10MB",
                "max_container_id_length": 15,
                "supported_units": ["kg", "lbs"],
                "weight_range_kg": "1-100000"
            }
        }
    
    def cleanup_uploaded_file(self, filename: str) -> bool:
        """
        Clean up uploaded file after processing.
        
        Args:
            filename: Name of file to delete
            
        Returns:
            True if deleted, False if not found
        """
        file_path = os.path.join(self.upload_dir, filename)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception:
            pass
        
        return False