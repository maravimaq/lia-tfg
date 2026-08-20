"""add product image url

Revision ID: 7de1d435a4db
Revises: fece58ab524a
Create Date: 2026-08-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7de1d435a4db"
down_revision: Union[str, Sequence[str], None] = "fece58ab524a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Añade la URL de imagen a los productos."""
    op.add_column(
        "productos",
        sa.Column("imagen_url", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Elimina la URL de imagen de los productos."""
    op.drop_column("productos", "imagen_url")