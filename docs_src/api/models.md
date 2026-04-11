# Models

Pure Python dataclasses used throughout pycommence-vibes. No COM references.

## Field Types

::: pycommence_vibes.models.FieldType
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

::: pycommence_vibes.models.FieldInfo

::: pycommence_vibes.models.ConnectionInfo

::: pycommence_vibes.models.CategoryInfo

## Row / Result Models

::: pycommence_vibes.models.RowResult
    options:
      members:
        - columns
        - row_id
        - __getitem__
        - get

## Filter / Sort Descriptors

::: pycommence_vibes.models.FilterType

::: pycommence_vibes.models.FilterClause

::: pycommence_vibes.models.SortSpec

::: pycommence_vibes.models.RelatedColumn

