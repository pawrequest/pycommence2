# Models

Pure Python dataclasses used throughout pycommence. No COM references.

## Field Types

::: pycommence.models.FieldType
    options:
      members:
        - TEXT
        - NUMBER
        - DATE
        - TELEPHONE
        - CHECK_BOX
        - NAME
        - DATA_FILE
        - IMAGE
        - TIME
        - EXCEL_CELL
        - CALCULATION
        - SEQUENCE
        - SELECTION
        - EMAIL
        - URL
        - from_code

## Schema Models

::: pycommence.models.FieldInfo

::: pycommence.models.ConnectionInfo

::: pycommence.models.CategoryInfo

## Row / Result Models

::: pycommence.models.RowResult
    options:
      members:
        - columns
        - row_id
        - __getitem__
        - get

## Filter / Sort Descriptors

::: pycommence.models.FilterType

::: pycommence.models.FilterClause

::: pycommence.models.SortSpec

::: pycommence.models.RelatedColumn
