#!/usr/bin/env python3
"""Populate Weight Service with test data to verify calculations."""

import requests
import time
import json
import random
import argparse
import shutil
import os
from datetime import datetime
from typing import Dict, Any


# Service URLs - access directly via service names in Docker network
WEIGHT_URL = "http://weight-service:5001"
BILLING_URL = "http://billing-service:5002" 
SHIFT_URL = "http://shift-service:5003"

# For backward compatibility
BASE_URL = WEIGHT_URL


def wait_for_services():
    """Wait for all services to be healthy."""
    services = [
        ("Weight Service", f"{WEIGHT_URL}/health"),
        ("Billing Service", f"{BILLING_URL}/health"), 
        ("Shift Service", f"{SHIFT_URL}/health")
    ]
    
    print("Waiting for all services to be ready...")
    
    for service_name, health_url in services:
        print(f"  Checking {service_name}...")
        for i in range(30):
            try:
                response = requests.get(health_url, timeout=2)
                if response.status_code == 200:
                    print(f"  ✅ {service_name} is ready!")
                    break
            except:
                pass
            time.sleep(2)
        else:
            print(f"  ❌ {service_name} not available")
            return False
    
    print("✅ All services are ready!")
    return True

def wait_for_service():
    """Wait for service to be healthy (backward compatibility)."""
    return wait_for_services()


def upload_container_weights():
    """Upload container weight data."""
    print("\n📦 Uploading container weights...")
    
    # Upload CSV files
    response = requests.post(
        f"{BASE_URL}/batch-weight",
        json={"file": "containers1.csv"}
    )
    print(f"containers1.csv upload: {response.status_code} - {response.json()}")
    
    response = requests.post(
        f"{BASE_URL}/batch-weight",
        json={"file": "containers2.csv"}
    )
    print(f"containers2.csv upload: {response.status_code} - {response.json()}")
    
    # Upload truck weights JSON file
    response = requests.post(
        f"{BASE_URL}/batch-weight",
        json={"file": "trucks.json"}
    )
    print(f"trucks.json upload: {response.status_code} - {response.json()}")


def upload_rates_excel():
    """Upload rates Excel file to billing service."""
    print("\n📊 Uploading rates Excel file...")
    
    try:
        # First copy rates.xlsx to billing service /in directory
        # In Docker environment, this would be a shared volume mount
        billing_in_path = "/shared/billing-in"
        if os.path.exists("rates.xlsx"):
            os.makedirs(billing_in_path, exist_ok=True)
            shutil.copy("rates.xlsx", f"{billing_in_path}/rates.xlsx")
            print("  📁 Copied rates.xlsx to billing service /in directory")
        else:
            print("  ⚠️  rates.xlsx not found in populate-data directory")
            return
        
        # Call the billing service API to upload rates from the /in directory
        response = requests.post(
            f"{BILLING_URL}/rates/from-directory",
            json={"file": "rates.xlsx"}
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"  ✅ Rates Excel uploaded successfully: {result.get('message', 'Success')}")
        else:
            print(f"  ⚠️  Rates upload returned status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"      Error: {error_detail}")
            except:
                print(f"      Response: {response.text}")
                
    except Exception as e:
        print(f"  ❌ Error uploading rates Excel: {e}")
        print("  ℹ️  Will proceed with hardcoded rates as fallback")


def populate_billing_data():
    """Populate billing service with providers, trucks, and rates."""
    print("\n💰 Populating billing data...")
    
    # First, try to upload rates from Excel file
    upload_rates_excel()
    
    # Create providers - ensure at least 5 providers
    providers_data = [
        {"name": "Citrus Valley Co-op"},
        {"name": "Golden Grove Farms"}, 
        {"name": "Sunshine Orchards"},
        {"name": "Jordan Valley Citrus"},
        {"name": "Galilee Groves"},
        {"name": "Upper Galilee Citrus"},
        {"name": "Mount Hermon Groves"}
    ]
    
    provider_ids = {}
    
    # Create providers - note: billing service uses /provider (singular) not /providers (plural)
    for provider in providers_data:
        try:
            response = requests.post(f"{BILLING_URL}/provider", json=provider)
            if response.status_code in [200, 201]:
                result = response.json()
                provider_ids[provider["name"]] = result.get("id")
                print(f"  ✅ Provider created: {provider['name']} (ID: {result.get('id')})")
            elif response.status_code == 409:  # Conflict - already exists
                print(f"  ℹ️  Provider already exists: {provider['name']}")
                # For existing providers, we'd need to implement a GET endpoint or handle this differently
                # For now, assign a placeholder ID - this should be improved in the billing service
                provider_ids[provider["name"]] = len(provider_ids) + 1
            else:
                print(f"  ⚠️  Could not create provider {provider['name']}: {response.status_code}")
                # Assign placeholder ID so trucks can still be created
                provider_ids[provider["name"]] = len(provider_ids) + 1
        except Exception as e:
            print(f"  ❌ Error creating provider {provider['name']}: {e}")
            # Assign placeholder ID so trucks can still be created  
            provider_ids[provider["name"]] = len(provider_ids) + 1
    
    print(f"  📊 Total providers available: {len(provider_ids)}")
    
    # Create trucks linked to providers - ensure proper linking
    trucks_data = [
        {"id": "T-14964", "provider_name": "Citrus Valley Co-op"},
        {"id": "T-16474", "provider_name": "Golden Grove Farms"},
        {"id": "T-12345", "provider_name": "Sunshine Orchards"},
        {"id": "T-88888", "provider_name": "Jordan Valley Citrus"},
        {"id": "T-99999", "provider_name": "Galilee Groves"},
        {"id": "T-55555", "provider_name": "Citrus Valley Co-op"},
        {"id": "T-66666", "provider_name": "Golden Grove Farms"},
        {"id": "T-77777", "provider_name": "Sunshine Orchards"},
        {"id": "T-33333", "provider_name": "Jordan Valley Citrus"},
        {"id": "T-44444", "provider_name": "Galilee Groves"},
        {"id": "T-22222", "provider_name": "Upper Galilee Citrus"},
        {"id": "T-11111", "provider_name": "Mount Hermon Groves"}
    ]
    
    for truck in trucks_data:
        provider_id = provider_ids.get(truck["provider_name"])
        if not provider_id:
            print(f"  ❌ No provider ID found for {truck['provider_name']}, skipping truck {truck['id']}")
            continue
            
        truck_data = {
            "id": truck["id"],
            "provider_id": provider_id
        }
        try:
            response = requests.post(f"{BILLING_URL}/truck", json=truck_data)
            if response.status_code in [200, 201]:
                print(f"  ✅ Truck registered: {truck['id']} -> {truck['provider_name']} (Provider ID: {provider_id})")
            else:
                print(f"  ⚠️  Could not register truck {truck['id']}: {response.status_code}")
                if response.status_code == 409:  # Truck already exists
                    print(f"      Truck {truck['id']} may already exist")
        except Exception as e:
            print(f"  ❌ Error registering truck {truck['id']}: {e}")
    
    # Create rates for different citrus products
    rates_data = [
        {"product_id": "Valencia", "rate": 120, "scope": "ALL"},
        {"product_id": "Tangerine", "rate": 135, "scope": "ALL"},
        {"product_id": "Mandarin", "rate": 140, "scope": "ALL"},
        {"product_id": "Grapefruit", "rate": 110, "scope": "ALL"},
        {"product_id": "Clementine", "rate": 145, "scope": "ALL"},
        {"product_id": "Shamuti", "rate": 125, "scope": "ALL"},
        {"product_id": "Blood Orange", "rate": 150, "scope": "ALL"},
        {"product_id": "Navel Orange", "rate": 130, "scope": "ALL"},
        {"product_id": "Pomelo", "rate": 100, "scope": "ALL"},
        {"product_id": "Lemon", "rate": 115, "scope": "ALL"},
        # Premium rates for specific providers
        {"product_id": "Valencia", "rate": 135, "scope": "Citrus Valley Co-op"},
        {"product_id": "Mandarin", "rate": 155, "scope": "Golden Grove Farms"}
    ]
    
    for rate in rates_data:
        try:
            response = requests.post(f"{BILLING_URL}/rates", json=rate)
            if response.status_code in [200, 201]:
                scope_info = f"({rate['scope']})" if rate['scope'] != 'ALL' else "(General)"
                print(f"  ✅ Rate set: {rate['product_id']} = ${rate['rate']}/ton {scope_info}")
            else:
                print(f"  ⚠️  Rate may already exist: {rate['product_id']}")
        except Exception as e:
            print(f"  ❌ Error setting rate for {rate['product_id']}: {e}")


def populate_shift_data():
    """Populate shift service with operators and active shifts."""
    print("\n👥 Populating shift data...")
    
    # The operators are already created by initial_operators.sql
    # Let's just start shifts for some operators
    
    operators_shifts = [
        {"operator_id": "OP001", "shift_type": "MORNING", "name": "David Cohen"},
        {"operator_id": "OP003", "shift_type": "AFTERNOON", "name": "Michael Green"},
        {"operator_id": "OP005", "shift_type": "MORNING", "name": "Yossi Mizrahi"}
    ]
    
    for shift_info in operators_shifts:
        shift_data = {
            "operator_id": shift_info["operator_id"],
            "shift_type": shift_info["shift_type"],
            "notes": f"Automated shift start for demo data population"
        }
        
        try:
            response = requests.post(f"{SHIFT_URL}/shifts", json=shift_data)
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"  ✅ Shift started: {shift_info['name']} ({shift_info['shift_type']}) - ID: {result.get('id', 'N/A')}")
            else:
                print(f"  ⚠️  Could not start shift for {shift_info['name']}: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Error starting shift for {shift_info['name']}: {e}")
    
    # Check operators
    try:
        response = requests.get(f"{SHIFT_URL}/operators")
        if response.status_code == 200:
            operators = response.json()
            print(f"  📊 Available operators: {len(operators)}")
            for op in operators[:3]:  # Show first 3
                print(f"      {op.get('id', 'N/A')}: {op.get('name', 'N/A')} ({op.get('role', 'N/A')})")
    except Exception as e:
        print(f"  ❌ Error checking operators: {e}")


def create_weighing_session(truck_id: str, containers: str, in_weight: int, out_weight: int, produce: str = "Oranges", realistic_timing: bool = False):
    """Create a complete IN/OUT weighing session with optional realistic timing."""
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"\n🚚 [{current_time}] Truck {truck_id} arriving at gate...")
    
    if realistic_timing:
        print(f"   📝 Driver presenting documents...")
        time.sleep(random.uniform(1, 3))  # Document check time
    
    # IN transaction
    print(f"   ⚖️  Truck moving to weighing scale...")
    if realistic_timing:
        time.sleep(random.uniform(2, 5))  # Time to position truck on scale
    
    in_data = {
        "direction": "in",
        "truck": truck_id,
        "containers": containers,
        "weight": in_weight,
        "unit": "kg",
        "produce": produce,
        "force": True  # Force to allow re-running the script
    }
    
    in_response = requests.post(f"{BASE_URL}/weight", json=in_data)
    if in_response.status_code != 200:
        print(f"❌ IN failed: {in_response.json()}")
        return
    
    in_result = in_response.json()
    session_id = in_result["id"]
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"✅ [{current_time}] IN weighing complete: Session {session_id}")
    print(f"   📊 Gross weight: {in_weight} kg")
    print(f"   🥤 Produce: {produce}")
    print(f"   📦 Containers: {containers}")
    
    if realistic_timing:
        print(f"   🚛 Truck proceeding to unloading area...")
        # Realistic unloading time based on weight (heavier loads take longer)
        unload_time_minutes = max(5, (in_weight - out_weight) / 1000 * 2)  # ~2 minutes per ton
        unload_time_seconds = min(unload_time_minutes * 60, 180)  # Cap at 3 minutes for demo
        
        print(f"   ⏳ Estimated unloading time: {unload_time_minutes:.1f} minutes")
        print(f"   🔄 Unloading {(in_weight - out_weight):,} kg of {produce}...")
        
        # Show progress during unloading
        for i in range(int(unload_time_seconds / 10)):
            time.sleep(10)
            progress = ((i + 1) * 10 / unload_time_seconds) * 100
            print(f"   📈 Unloading progress: {progress:.0f}%")
        
        print(f"   ✅ Unloading complete!")
        print(f"   🚛 Truck returning to weighing scale...")
        time.sleep(random.uniform(2, 4))  # Time to return to scale
    
    # OUT transaction
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"   ⚖️  [{current_time}] Final weighing (empty truck)...")
    
    out_data = {
        "direction": "out",
        "truck": truck_id,
        "containers": containers,
        "weight": out_weight,
        "unit": "kg"
    }
    
    out_response = requests.post(f"{BASE_URL}/weight", json=out_data)
    if out_response.status_code != 200:
        print(f"❌ OUT failed: {out_response.json()}")
        return
    
    out_result = out_response.json()
    current_time = datetime.now().strftime("%H:%M:%S")
    print(f"✅ [{current_time}] OUT weighing complete: Session {out_result['id']}")
    print(f"   📊 Empty truck weight (tara): {out_result['truck_tara']} kg")
    print(f"   🥤 Net fruit delivered: {out_result['neto']:,} kg")
    
    # Calculate value estimate (mock pricing)
    price_per_kg = random.uniform(0.8, 1.5)  # Mock price range
    estimated_value = out_result['neto'] * price_per_kg
    print(f"   💰 Estimated value: ${estimated_value:.2f} ({price_per_kg:.2f}/kg)")
    
    # Verify calculations
    expected_neto = in_weight - out_weight
    if out_result['neto'] == expected_neto:
        print(f"✅ Weight calculation verified: {expected_neto:,} kg fruit delivered")
    else:
        print(f"❌ Calculation error: Expected {expected_neto}, got {out_result['neto']}")
    
    if realistic_timing:
        print(f"   🚪 Truck exiting facility...")
        time.sleep(random.uniform(1, 2))
        print(f"   ✅ Transaction complete! Have a safe trip!")
    
    return session_id


def populate_test_data(realistic_timing: bool = False):
    """Populate various test scenarios with realistic citrus varieties for Gan Shmuel juice factory."""
    print("\n🎯 Creating test weighing sessions with citrus varieties for billing rates...")
    
    if realistic_timing:
        print("🕐 REALISTIC TIMING MODE ENABLED")
        print("   This will simulate actual juice factory operations with realistic delays")
        print("   - Document checks: 1-3 seconds")
        print("   - Scale positioning: 2-5 seconds")
        print("   - Unloading time: Based on cargo weight (~2 min/ton, capped at 3 min)")
        print("   - Return to scale: 2-4 seconds")
        print("   - Between trucks: 3-8 seconds")
        print("\n⏰ Starting operations...\n")
    
    trucks_data = [
        # Test Case 1: Valencia oranges - most common variety
        ("T-14964", "C-35434,C-36882", 8500, 1200, "Valencia"),
        
        # Test Case 2: Tangerine - heavy load with multiple containers
        ("T-16474", "C-40277,C-45237,C-50462,C-73281", 15000, 2500, "Tangerine"),
        
        # Test Case 3: Mandarin - small load
        ("T-12345", "C-10001,C-10002", 5000, 1000, "Mandarin"),
        
        # Test Case 4: Grapefruit - mixed unit containers
        ("T-88888", "C-30001,C-30002", 6800, 1300, "Grapefruit"),
        
        # Test Case 5: Clementine - large shipment
        ("T-99999", "K-8263,K-8328,K-8639,K-8971,C-66700,C-68875", 25000, 3500, "Clementine"),
        
        # Test Case 6: Shamuti (Israeli orange variety)
        ("T-55555", "C-10003,C-10004,C-10005", 4500, 1100, "Shamuti"),
        
        # Test Case 7: Valencia - another shipment
        ("T-66666", "C-20001,C-20002", 7200, 1400, "Valencia"),
        
        # Test Case 8: Mandarin - premium quality
        ("T-77777", "C-20003,C-20004,C-20005", 9800, 1800, "Mandarin"),
        
        # Test Case 9: Blood Orange (special variety)
        ("T-33333", "C-30003,C-30004", 5600, 1100, "Blood Orange"),
        
        # Test Case 10: Navel Orange
        ("T-44444", "C-30005,C-50797", 6900, 1300, "Navel Orange"),
        
        # Test Case 11: Pomelo
        ("T-22222", "C-52273,C-53813,C-54336", 11200, 1800, "Pomelo"),
        
        # Test Case 12: Lemon
        ("T-11111", "C-55011,C-55050", 4800, 1000, "Lemon")
    ]
    
    total_trucks = len(trucks_data)
    
    for i, (truck_id, containers, in_weight, out_weight, produce) in enumerate(trucks_data, 1):
        if realistic_timing and i > 1:
            # Realistic time between truck arrivals (3-8 seconds for demo, would be minutes in real life)
            wait_time = random.uniform(3, 8)
            print(f"\n⏳ [{datetime.now().strftime('%H:%M:%S')}] Waiting for next truck... ({wait_time:.1f}s)")
            print(f"📊 Progress: {i-1}/{total_trucks} trucks processed")
            time.sleep(wait_time)
        
        create_weighing_session(
            truck_id=truck_id,
            containers=containers,
            in_weight=in_weight,
            out_weight=out_weight,
            produce=produce,
            realistic_timing=realistic_timing
        )
    
    if realistic_timing:
        print(f"\n🏁 [{datetime.now().strftime('%H:%M:%S')}] All trucks processed!")
        print(f"✅ Successfully processed {total_trucks} trucks")
        print("📊 Daily operations summary:")
        total_fruit = sum(data[2] - data[3] for data in trucks_data)  # in_weight - out_weight
        print(f"   🥤 Total fruit processed: {total_fruit:,} kg")
        print(f"   🚚 Average per truck: {total_fruit//total_trucks:,} kg")
        print("🎉 End of shift - Great work team!")


def verify_data():
    """Verify the populated data."""
    print("\n📊 Verifying data...")
    
    # Get all transactions
    response = requests.get(f"{BASE_URL}/weight")
    if response.status_code == 200:
        transactions = response.json()
        print(f"\nTotal transactions: {len(transactions)}")
        
        # Count by direction
        in_count = sum(1 for t in transactions if t['direction'] == 'in')
        out_count = sum(1 for t in transactions if t['direction'] == 'out')
        print(f"IN transactions: {in_count}")
        print(f"OUT transactions: {out_count}")
        
        # Show some completed sessions
        print("\n📈 Completed sessions with calculations:")
        for t in transactions:
            if t['direction'] == 'out' and t.get('neto') not in [None, 'na']:
                print(f"\nSession: {t['id']}")
                print(f"  Truck: {t.get('truck', 'N/A')}")
                print(f"  Net Weight: {t['neto']} kg")
                print(f"  Containers: {len(t.get('containers', []))} containers")
    
    # Check unknown containers
    response = requests.get(f"{BASE_URL}/unknown")
    if response.status_code == 200:
        unknowns = response.json()
        print(f"\n❓ Unknown containers: {len(unknowns)}")
        if unknowns:
            print(f"   First 5: {unknowns[:5]}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description='Populate Weight Service with test data')
    parser.add_argument('--realistic', '-r', action='store_true', 
                       help='Enable realistic timing mode to demonstrate actual factory operations')
    parser.add_argument('--fast', '-f', action='store_true',
                       help='Fast mode (default) - no delays, just populate data')
    
    args = parser.parse_args()
    
    # Default to fast mode if no flags specified
    realistic_timing = args.realistic and not args.fast
    
    print("🚀 Weight Service Data Population Script")
    print("=" * 50)
    
    if realistic_timing:
        print("🕐 REALISTIC DEMONSTRATION MODE")
        print("   This will take several minutes to complete...")
        print("   Press Ctrl+C to stop at any time")
        print("=" * 50)
    else:
        print("⚡ FAST MODE - Quick data population")
        print("   Use --realistic flag for demonstration mode")
        print("=" * 50)
    
    if not wait_for_services():
        print("❌ Services not available. Make sure docker-compose is running.")
        return
    
    try:
        # Step 1: Populate billing data (providers, trucks, rates)
        populate_billing_data()
        time.sleep(1)
        
        # Step 2: Populate shift data (operators, shifts)
        populate_shift_data()
        time.sleep(1)
        
        # Step 3: Upload container weights
        upload_container_weights()
        time.sleep(2)
        
        # Step 4: Create test weighing sessions
        populate_test_data(realistic_timing=realistic_timing)
        
        # Verify results
        verify_data()
        
        print("\n✅ Data population complete!")
        
        if realistic_timing:
            print("\n🎬 Realistic demonstration finished!")
            print("   This simulated a typical day at Gan Shmuel juice factory")
        
        print("\n📝 You can now test the system:")
        print("   - Check transactions: GET http://localhost:5001/weight")
        print("   - Check specific truck: GET http://localhost:5001/item/T-14964")
        print("   - Check health: GET http://localhost:5001/health")
        print("   - Frontend: http://localhost:3000")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation interrupted by user")
        print("✅ Partial data may have been populated")
        print("   Run the script again to complete or continue")


if __name__ == "__main__":
    main()