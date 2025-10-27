# Weight Service  - Architecture & Flow Diagrams

This document provides comprehensive diagrams for understanding the Weight Service  architecture, API flows, and business logic using Mermaid diagrams.

## Table of Contents
- [System Architecture](#system-architecture)
- [API Flow Diagrams](#api-flow-diagrams)
- [Data Flow Diagrams](#data-flow-diagrams)
- [Business Logic Flows](#business-logic-flows)
- [Database Schema Relationships](#database-schema-relationships)
- [Error Handling Flows](#error-handling-flows)

## System Architecture

### Service Architecture Overview
```mermaid
graph TB
    subgraph "External Systems"
        CLIENT[Client Applications]
        BILLING[Billing Service]
        FILES[File System /in]
    end
    
    subgraph "Weight Service V2"
        subgraph "API Layer"
            ROUTER_W[Weight Router]
            ROUTER_B[Batch Router]
            ROUTER_Q[Query Router]
            ROUTER_H[Health Router]
        end
        
        subgraph "Service Layer"
            WS[Weight Service]
            CS[Container Service]
            FS[File Service]
            QS[Query Service]
            SS[Session Service]
        end
        
        subgraph "Repository Layer"
            TR[Transaction Repository]
            CR[Container Repository]
            SR[Session Repository]
        end
        
        subgraph "Utils"
            CALC[Calculations]
            VALID[Validators]
            EXCEPT[Exceptions]
            DATETIME[DateTime Utils]
        end
    end
    
    subgraph "Data Layer"
        DB[(MySQL Database)]
        TABLES[containers_registered<br/>transactions]
    end
    
    CLIENT --> ROUTER_W
    CLIENT --> ROUTER_B
    CLIENT --> ROUTER_Q
    CLIENT --> ROUTER_H
    BILLING --> ROUTER_Q
    
    ROUTER_W --> WS
    ROUTER_B --> FS
    ROUTER_Q --> QS
    ROUTER_H --> QS
    
    WS --> TR
    WS --> CR
    WS --> SS
    FS --> CR
    QS --> TR
    QS --> CR
    SS --> TR
    
    TR --> DB
    CR --> DB
    SR --> DB
    
    WS --> CALC
    WS --> VALID
    FS --> VALID
    
    FILES --> FS
    DB --> TABLES
```

### Technology Stack Layers
```mermaid
graph TD
    subgraph "Application Layer"
        FASTAPI[FastAPI Framework]
        PYDANTIC[Pydantic V2 Validation]
        UVICORN[Uvicorn ASGI Server]
    end
    
    subgraph "Business Logic Layer"
        SERVICES[Service Classes]
        REPOS[Repository Pattern]
        MODELS[Pydantic Models]
    end
    
    subgraph "Data Access Layer"
        SQLALCHEMY[SQLAlchemy 2.0 ORM]
        ALEMBIC[Alembic Migrations]
        ASYNCIO[Async/Await Support]
    end
    
    subgraph "Infrastructure Layer"
        MYSQL[MySQL 8.0 Database]
        DOCKER[Docker Containers]
        UV[uv Package Manager]
    end
    
    FASTAPI --> SERVICES
    PYDANTIC --> MODELS
    SERVICES --> REPOS
    REPOS --> SQLALCHEMY
    SQLALCHEMY --> MYSQL
    ALEMBIC --> MYSQL
```

## API Flow Diagrams

### Weight Recording Flow (POST /weight)
```mermaid
sequenceDiagram
    participant C as Client
    participant R as Weight Router
    participant WS as Weight Service
    participant TR as Transaction Repo
    participant CR as Container Repo
    participant DB as Database
    
    C->>R: POST /weight
    Note over C,R: {direction: "in/out/none", truck, containers, weight, unit}
    
    R->>WS: record_weight(request)
    
    WS->>WS: validate_weight_range()
    WS->>WS: parse_container_list()
    
    alt direction == "out"
        WS->>TR: find_matching_in_transaction()
        TR->>DB: SELECT from transactions
        WS->>CR: get_container_weight_info()
        CR->>DB: SELECT from containers_registered
        WS->>WS: calculate_weights()
        WS->>TR: update_out_transaction()
        TR->>DB: UPDATE transactions
    else direction == "in"
        WS->>WS: generate_session_id()
        WS->>TR: create()
        TR->>DB: INSERT into transactions
    else direction == "none"
        WS->>WS: generate_session_id()
        WS->>TR: create()
        TR->>DB: INSERT into transactions
    end
    
    WS->>DB: COMMIT
    WS->>R: WeightResponse
    R->>C: HTTP 200 + Response JSON
```

### Batch Upload Flow (POST /batch-weight)
```mermaid
sequenceDiagram
    participant C as Client
    participant R as Batch Router
    participant FS as File Service
    participant CR as Container Repo
    participant DB as Database
    participant F as File System
    
    C->>R: POST /batch-weight
    Note over C,R: {file: "containers.csv"}
    
    R->>FS: process_batch_file(filename)
    FS->>F: read file from /in directory
    
    alt CSV file
        FS->>FS: parse_csv()
        Note over FS: Parse "id,weight" format
    else JSON file
        FS->>FS: parse_json()
        Note over FS: Parse [{id, weight, unit}] format
    end
    
    loop For each container
        FS->>FS: validate_container_data()
        FS->>CR: upsert_container()
        CR->>DB: INSERT/UPDATE containers_registered
    end
    
    FS->>DB: COMMIT
    FS->>R: BatchUploadResponse
    R->>C: HTTP 200 + Summary
```

### Query Flow (GET /weight)
```mermaid
sequenceDiagram
    participant C as Client
    participant R as Query Router
    participant QS as Query Service
    participant TR as Transaction Repo
    participant DB as Database
    
    C->>R: GET /weight?from=20240101000000&to=20240131235959&filter=in,out
    
    R->>QS: get_transactions(params)
    QS->>QS: parse_datetime_range()
    QS->>QS: parse_direction_filter()
    
    QS->>TR: find_transactions_by_criteria()
    TR->>DB: SELECT with WHERE conditions
    
    QS->>QS: format_transaction_response()
    QS->>R: List[TransactionResponse]
    R->>C: HTTP 200 + Transaction Array
```

## Data Flow Diagrams

### Weight Calculation Data Flow
```mermaid
flowchart TD
    START([Weight Recording Request])
    
    INPUT[Input Data:<br/>- Direction<br/>- Truck ID<br/>- Containers<br/>- Weight<br/>- Unit]
    
    PARSE[Parse & Validate:<br/>- Container IDs<br/>- Weight Range<br/>- Unit Conversion]
    
    DIRECTION{Direction Type?}
    
    IN_FLOW[IN Direction Flow:<br/>1. Generate Session ID<br/>2. Store Gross Weight<br/>3. No Calculations]
    
    OUT_FLOW[OUT Direction Flow:<br/>1. Find Matching IN<br/>2. Get Container Weights<br/>3. Calculate Net Weight]
    
    NONE_FLOW[NONE Direction Flow:<br/>1. Generate Session ID<br/>2. Store Weight<br/>3. No Calculations]
    
    CALC[Weight Calculations:<br/>Truck Tara = Bruto(IN) - Bruto(OUT) - Σ(Container Tara)<br/>Net Weight = Bruto(IN) - Truck Tara - Σ(Container Tara)]
    
    STORE[Store Results:<br/>- Update IN transaction<br/>- Create OUT transaction<br/>- Commit to Database]
    
    RESPONSE[Return Response:<br/>- Session ID<br/>- Weight Values<br/>- Calculated Results]
    
    START --> INPUT
    INPUT --> PARSE
    PARSE --> DIRECTION
    
    DIRECTION -->|in| IN_FLOW
    DIRECTION -->|out| OUT_FLOW
    DIRECTION -->|none| NONE_FLOW
    
    OUT_FLOW --> CALC
    CALC --> STORE
    
    IN_FLOW --> STORE
    NONE_FLOW --> STORE
    
    STORE --> RESPONSE
```

### Container Weight Management Flow
```mermaid
flowchart TD
    BATCH_START([Batch Upload Start])
    
    FILE_READ[Read File:<br/>- CSV: id,weight<br/>- JSON: [{id,weight,unit}]]
    
    PARSE{File Format?}
    
    CSV_PARSE[Parse CSV:<br/>- Split by lines<br/>- Extract id,weight pairs<br/>- Default unit: kg]
    
    JSON_PARSE[Parse JSON:<br/>- Deserialize array<br/>- Extract objects<br/>- Support unit field]
    
    VALIDATE[Validate Each Record:<br/>- Container ID format<br/>- Weight > 0<br/>- Unit conversion]
    
    UPSERT[Upsert Container:<br/>- INSERT if new<br/>- UPDATE if exists<br/>- Track processed count]
    
    BATCH_RESULT[Return Results:<br/>- Processed count<br/>- Skipped count<br/>- Error list]
    
    BATCH_START --> FILE_READ
    FILE_READ --> PARSE
    
    PARSE -->|CSV| CSV_PARSE
    PARSE -->|JSON| JSON_PARSE
    
    CSV_PARSE --> VALIDATE
    JSON_PARSE --> VALIDATE
    
    VALIDATE --> UPSERT
    UPSERT --> BATCH_RESULT
```

## Business Logic Flows

### Weighing Sequence Validation
```mermaid
flowchart TD
    VALIDATE_START([Validate Weighing Sequence])
    
    DIRECTION{Direction?}
    
    IN_LOGIC[IN Direction Logic:<br/>- Check for existing IN<br/>- Prevent duplicates<br/>- Allow with force=true]
    
    OUT_LOGIC[OUT Direction Logic:<br/>- Require matching IN<br/>- Validate container weights<br/>- Calculate if possible]
    
    NONE_LOGIC[NONE Direction Logic:<br/>- Always allowed<br/>- Standalone weighing<br/>- No sequence checks]
    
    CHECK_EXISTING{Existing IN<br/>Found?}
    
    CHECK_CONTAINERS{All Containers<br/>Registered?}
    
    FORCE_CHECK{Force Flag<br/>Enabled?}
    
    ALLOW[Allow Operation]
    REJECT[Reject Operation]
    
    VALIDATE_START --> DIRECTION
    
    DIRECTION -->|in| IN_LOGIC
    DIRECTION -->|out| OUT_LOGIC
    DIRECTION -->|none| NONE_LOGIC
    
    IN_LOGIC --> CHECK_EXISTING
    CHECK_EXISTING -->|Yes| FORCE_CHECK
    CHECK_EXISTING -->|No| ALLOW
    FORCE_CHECK -->|Yes| ALLOW
    FORCE_CHECK -->|No| REJECT
    
    OUT_LOGIC --> CHECK_EXISTING
    OUT_LOGIC --> CHECK_CONTAINERS
    CHECK_CONTAINERS -->|Yes| ALLOW
    CHECK_CONTAINERS -->|No| REJECT
    
    NONE_LOGIC --> ALLOW
```

### Weight Calculation Business Logic
```mermaid
flowchart TD
    CALC_START([Weight Calculation])
    
    INPUT_DATA[Input Data:<br/>- Bruto IN (kg)<br/>- Bruto OUT (kg)<br/>- Container IDs]
    
    GET_CONTAINERS[Get Container Weights:<br/>- Query containers_registered<br/>- Convert units to kg<br/>- Check for unknowns]
    
    UNKNOWN_CHECK{Unknown<br/>Containers?}
    
    CALC_TRUCK[Calculate Truck Tara:<br/>Truck Tara = Bruto(IN) - Bruto(OUT) - Σ(Container Tara)]
    
    CALC_NET[Calculate Net Weight:<br/>Net Weight = Bruto(IN) - Truck Tara - Σ(Container Tara)]
    
    VALIDATE_RESULT[Validate Results:<br/>- Truck Tara ≥ 0<br/>- Net Weight ≥ 0<br/>- Logical consistency]
    
    RETURN_SUCCESS[Return Calculated Values]
    RETURN_ERROR[Return Error: Unknown Containers]
    
    CALC_START --> INPUT_DATA
    INPUT_DATA --> GET_CONTAINERS
    GET_CONTAINERS --> UNKNOWN_CHECK
    
    UNKNOWN_CHECK -->|Yes| RETURN_ERROR
    UNKNOWN_CHECK -->|No| CALC_TRUCK
    
    CALC_TRUCK --> CALC_NET
    CALC_NET --> VALIDATE_RESULT
    VALIDATE_RESULT --> RETURN_SUCCESS
```

## Database Schema Relationships

### Entity Relationship Diagram
```mermaid
erDiagram
    containers_registered {
        string container_id PK
        int weight
        string unit
        datetime created_at
        datetime updated_at
    }
    
    transactions {
        int id PK
        string session_id
        datetime datetime
        string direction
        string truck
        text containers
        int bruto
        int truck_tara
        int neto
        string produce
        datetime created_at
    }
    
    containers_registered ||--o{ transactions : "used_in"
```

### Data Access Patterns
```mermaid
flowchart TD
    subgraph "Read Operations"
        R1[Find Matching IN Transaction]
        R2[Get Container Weights]
        R3[Query Transactions by Date]
        R4[Get Session Details]
        R5[List Unknown Containers]
    end
    
    subgraph "Write Operations"
        W1[Create Transaction]
        W2[Update Transaction Calculations]
        W3[Upsert Container Weights]
        W4[Batch Container Upload]
    end
    
    subgraph "Database Tables"
        T1[(transactions)]
        T2[(containers_registered)]
    end
    
    R1 --> T1
    R2 --> T2
    R3 --> T1
    R4 --> T1
    R5 --> T1
    R5 --> T2
    
    W1 --> T1
    W2 --> T1
    W3 --> T2
    W4 --> T2
```

## Error Handling Flows

### Error Classification and Handling
```mermaid
flowchart TD
    ERROR_START([Error Detected])
    
    ERROR_TYPE{Error Type?}
    
    VALIDATION[Validation Error:<br/>- Invalid input format<br/>- Missing required fields<br/>- Range violations]
    
    BUSINESS[Business Logic Error:<br/>- Invalid sequence<br/>- Missing containers<br/>- Calculation errors]
    
    SYSTEM[System Error:<br/>- Database connection<br/>- File access<br/>- Network issues]
    
    FORMAT_400[Format HTTP 400:<br/>- Client error<br/>- Validation details<br/>- Actionable message]
    
    FORMAT_500[Format HTTP 500:<br/>- Server error<br/>- Generic message<br/>- Log detailed error]
    
    LOG_ERROR[Log Error Details:<br/>- Stack trace<br/>- Request context<br/>- Timestamp]
    
    RETURN_RESPONSE[Return Error Response]
    
    ERROR_START --> ERROR_TYPE
    
    ERROR_TYPE -->|Validation| VALIDATION
    ERROR_TYPE -->|Business| BUSINESS
    ERROR_TYPE -->|System| SYSTEM
    
    VALIDATION --> FORMAT_400
    BUSINESS --> FORMAT_400
    SYSTEM --> FORMAT_500
    
    FORMAT_400 --> LOG_ERROR
    FORMAT_500 --> LOG_ERROR
    
    LOG_ERROR --> RETURN_RESPONSE
```

### Retry and Recovery Patterns
```mermaid
flowchart TD
    OPERATION[Database Operation]
    
    EXECUTE{Execute<br/>Operation}
    
    SUCCESS[Operation Success]
    
    ERROR{Error Type?}
    
    TRANSIENT[Transient Error:<br/>- Connection timeout<br/>- Temporary lock<br/>- Network blip]
    
    PERMANENT[Permanent Error:<br/>- Constraint violation<br/>- Invalid data<br/>- Logic error]
    
    RETRY_CHECK{Retry Count<br/>< Max?}
    
    WAIT[Wait with<br/>Exponential Backoff]
    
    RETRY[Retry Operation]
    
    FAIL[Operation Failed]
    
    OPERATION --> EXECUTE
    EXECUTE -->|Success| SUCCESS
    EXECUTE -->|Error| ERROR
    
    ERROR -->|Transient| TRANSIENT
    ERROR -->|Permanent| PERMANENT
    
    TRANSIENT --> RETRY_CHECK
    RETRY_CHECK -->|Yes| WAIT
    RETRY_CHECK -->|No| FAIL
    WAIT --> RETRY
    RETRY --> EXECUTE
    
    PERMANENT --> FAIL
```

---

**Note**: These diagrams provide a comprehensive overview of the Weight Service  architecture and flows. They can be rendered using any Mermaid-compatible viewer or integrated into documentation systems that support Mermaid syntax.