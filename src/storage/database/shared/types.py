from sqlalchemy import BigInteger, Integer


# PostgreSQL keeps 64-bit identifiers; SQLite needs INTEGER exactly for
# automatic row-id generation.
BIGINT_PRIMARY_KEY = BigInteger().with_variant(Integer, "sqlite")
