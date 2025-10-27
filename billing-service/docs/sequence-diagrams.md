# Billing Service Sequence Diagrams

This document contains mermaid sequence diagrams showing the software flows within the Billing Service.

## 1. Bill Generation Flow (Main Business Logic)

```mermaid
sequenceDiagram
    participant Client
    participant BillsRouter
    participant BillService
    participant ProviderRepo
    participant TruckRepo
    participant RateRepo
    participant WeightClient
    participant WeightService
    participant Database

    Client->>BillsRouter: GET /bill/{provider_id}?from=date&to=date
    BillsRouter->>BillService: generate_bill(provider_id, from_date, to_date)
    
    BillService->>ProviderRepo: get_by_id(provider_id)
    ProviderRepo->>Database: SELECT * FROM Provider WHERE id = ?
    Database-->>ProviderRepo: provider record
    ProviderRepo-->>BillService: Provider object
    
    BillService->>TruckRepo: get_by_provider(provider_id)
    TruckRepo->>Database: SELECT * FROM Trucks WHERE provider_id = ?
    Database-->>TruckRepo: truck records
    TruckRepo-->>BillService: List[Truck]
    
    BillService->>RateRepo: get_all()
    RateRepo->>Database: SELECT * FROM Rates
    Database-->>RateRepo: rate records
    RateRepo-->>BillService: List[Rate]
    
    BillService->>WeightClient: get_transactions(from_date, to_date)
    WeightClient->>WeightService: GET /weight?from={date}&to={date}
    WeightService-->>WeightClient: transaction data
    WeightClient-->>BillService: List[Transaction]
    
    BillService->>BillService: _filter_provider_transactions(transactions, truck_ids)
    BillService->>BillService: _calculate_bill_totals(transactions, rates, provider_id)
    BillService->>BillService: _find_applicable_rate() for each product
    
    BillService-->>BillsRouter: BillResponse
    BillsRouter-->>Client: JSON bill with products and totals
```

## 2. Rate Management Flow

```mermaid
sequenceDiagram
    participant Client
    participant RatesRouter
    participant ExcelHandler
    participant RateRepo
    participant Database
    participant FileSystem

    Client->>RatesRouter: POST /rates {file: "rates.xlsx"}
    RatesRouter->>ExcelHandler: read_rates_from_excel(filename)
    
    ExcelHandler->>FileSystem: read Excel from /in/rates.xlsx
    FileSystem-->>ExcelHandler: Excel file content
    ExcelHandler->>ExcelHandler: validate columns (Product, Rate, Scope)
    ExcelHandler->>ExcelHandler: convert rows to Rate objects
    ExcelHandler-->>RatesRouter: List[Rate]
    
    RatesRouter->>RateRepo: clear_all()
    RateRepo->>Database: DELETE FROM Rates
    Database-->>RateRepo: clear confirmation
    
    RatesRouter->>RateRepo: create_batch(rates)
    loop For each rate
        RateRepo->>Database: INSERT INTO Rates (product_id, rate, scope)
        Database-->>RateRepo: insert confirmation
    end
    RateRepo-->>RatesRouter: created count
    
    RatesRouter-->>Client: RateUploadResponse {message, count}
```

## 3. Truck Registration Flow

```mermaid
sequenceDiagram
    participant Client
    participant TrucksRouter
    participant TruckRepo
    participant Database

    Client->>TrucksRouter: POST /truck {id, provider_id}
    TrucksRouter->>TruckRepo: create_or_update(truck_id, provider_id)
    
    TruckRepo->>Database: SELECT id FROM Provider WHERE id = ?
    Database-->>TruckRepo: provider exists check
    
    alt Provider exists
        TruckRepo->>Database: INSERT INTO Trucks ON DUPLICATE KEY UPDATE
        Database-->>TruckRepo: truck record
        TruckRepo-->>TrucksRouter: Truck object
        TrucksRouter-->>Client: 201 TruckResponse
    else Provider not found
        TruckRepo-->>TrucksRouter: NotFoundError
        TrucksRouter-->>Client: 404 Provider not found
    end
```

## 4. Weight Service Integration with Retry Logic

```mermaid
sequenceDiagram
    participant BillService
    participant WeightClient
    participant WeightService

    BillService->>WeightClient: get_transactions(from_date, to_date)
    
    loop max_retries = 3
        WeightClient->>WeightService: GET /weight?from={date}&to={date}
        
        alt Success Response
            WeightService-->>WeightClient: 200 + transaction data
            WeightClient-->>BillService: List[Transaction]
        else Timeout/Error
            WeightService-->>WeightClient: timeout/error
            Note over WeightClient: exponential backoff: sleep(2^attempt)
            WeightClient->>WeightClient: increment attempt counter
        end
    end
    
    alt All retries failed
        WeightClient-->>BillService: WeightServiceError
    end
```

## 5. Provider Management Flow

```mermaid
sequenceDiagram
    participant Client
    participant ProvidersRouter
    participant ProviderRepo
    participant Database

    Client->>ProvidersRouter: POST /provider {name}
    ProvidersRouter->>ProviderRepo: create(name)
    
    ProviderRepo->>Database: SELECT id FROM Provider WHERE name = ?
    Database-->>ProviderRepo: duplicate check result
    
    alt No duplicate found
        ProviderRepo->>Database: INSERT INTO Provider (name) VALUES (?)
        Database-->>ProviderRepo: new provider with last_insert_id
        ProviderRepo-->>ProvidersRouter: Provider object
        ProvidersRouter-->>Client: 201 ProviderResponse
    else Duplicate name exists
        ProviderRepo-->>ProvidersRouter: DuplicateError
        ProvidersRouter-->>Client: 409 Provider name must be unique
    end
```

## 6. Truck Details Retrieval Flow

```mermaid
sequenceDiagram
    participant Client
    participant TrucksRouter
    participant TruckRepo
    participant WeightClient
    participant WeightService
    participant Database

    Client->>TrucksRouter: GET /truck/{truck_id}?from=date&to=date
    TrucksRouter->>TruckRepo: get_by_id(truck_id)
    TruckRepo->>Database: SELECT * FROM Trucks WHERE id = ?
    Database-->>TruckRepo: truck record
    TruckRepo-->>TrucksRouter: Truck object
    
    alt Truck exists in billing DB
        TrucksRouter->>WeightClient: get_item_details(truck_id, from_date, to_date)
        WeightClient->>WeightService: GET /item/{truck_id}?from={date}&to={date}
        WeightService-->>WeightClient: truck details (tara, sessions)
        WeightClient-->>TrucksRouter: WeightItem object
        TrucksRouter-->>Client: TruckDetails {id, tara, sessions}
    else Truck not found
        TrucksRouter-->>Client: 404 Truck not found
    end
```

## 7. Rate Download Flow

```mermaid
sequenceDiagram
    participant Client
    participant RatesRouter
    participant RateRepo
    participant ExcelHandler
    participant Database

    Client->>RatesRouter: GET /rates
    RatesRouter->>RateRepo: get_all()
    RateRepo->>Database: SELECT * FROM Rates
    Database-->>RateRepo: all rate records
    RateRepo-->>RatesRouter: List[Rate]
    
    RatesRouter->>ExcelHandler: create_rates_excel(rates)
    ExcelHandler->>ExcelHandler: generate Excel with Product, Rate, Scope columns
    ExcelHandler-->>RatesRouter: Excel file stream
    
    RatesRouter-->>Client: StreamingResponse (rates.xlsx download)
```

## Architecture Summary

The billing service follows a clean architecture with these key components:

- **API Layer**: FastAPI routers handling HTTP requests
- **Service Layer**: Business logic and orchestration
- **Repository Layer**: Data access abstraction
- **External Integration**: Weight service client with retry logic
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes

### Key Design Patterns

1. **Repository Pattern**: Clean separation of data access logic
2. **Service Layer Pattern**: Business logic encapsulation
3. **Retry Pattern**: Resilient external service integration
4. **Exception Handling Pattern**: Consistent error responses

### Business Logic Highlights

- **Rate Precedence**: Provider-specific rates override general rates
- **Bill Calculation**: Neto weight × rate = payment amount
- **Transaction Filtering**: Only processes transactions for provider's trucks
- **Excel Processing**: Batch upload/download of pricing rates