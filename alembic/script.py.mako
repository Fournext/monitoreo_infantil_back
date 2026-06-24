"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def create_index_if_table_exists(
    index_name: str,
    table_name: str,
    column_name: str,
    using: str = "gist"
) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = '{table_name}'
            ) THEN
                EXECUTE 'CREATE INDEX IF NOT EXISTS {index_name}
                ON {table_name} USING {using} ({column_name})';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    ${upgrades if upgrades else "pass"}

    create_index_if_table_exists(
        "idx_daycares_area",
        "daycares",
        "area"
    )

    create_index_if_table_exists(
        "idx_child_locations_point",
        "child_locations",
        "point"
    )

    create_index_if_table_exists(
        "idx_current_child_locations_point",
        "current_child_locations",
        "point"
    )


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}