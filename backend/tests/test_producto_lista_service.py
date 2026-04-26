import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch

from app.db.base import Base

from app.models.lista_compra import ListaCompra
from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.schemas.producto_lista import ProductoListaCreate, ProductoListaUpdate
from app.services.producto_lista_service import ProductoListaService


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def current_user():
    user = User()
    user.id_usuario = 1
    user.email = "test@test.com"
    user.estado = "activo"
    return user


@pytest.fixture
def lista():
    lista = ListaCompra()
    lista.id_lista = 1
    lista.nombre_lista = "Compra semanal"
    lista.usuario_id = 1
    lista.total_estimado = 0
    return lista


@pytest.fixture
def producto():
    producto = ProductoLista()
    producto.id_producto_lista = 1
    producto.nombre_producto = "Leche"
    producto.cantidad = 2
    producto.precio_estimado = 1.5
    producto.unidad_medida = "litros"
    producto.supermercado = "Mercadona"
    producto.lista_id = 1
    return producto


def test_create_producto_success(db, current_user, lista):
    producto_data = ProductoListaCreate(
        nombre_producto="Leche",
        cantidad=2,
        unidad_medida="litros",
        supermercado="Mercadona",
        precio_estimado=1.5,
        lista_id=1
    )

    producto_creado = ProductoLista(
        id_producto_lista=1,
        nombre_producto="Leche",
        cantidad=2,
        unidad_medida="litros",
        supermercado="Mercadona",
        precio_estimado=1.5,
        lista_id=1
    )

    productos_lista = [producto_creado]

    with patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo, \
         patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo:

        lista_repo.get_by_id.return_value = lista
        lista_repo.save.return_value = lista
        producto_repo.create.return_value = producto_creado
        producto_repo.get_by_lista_id.return_value = productos_lista

        result = ProductoListaService.create_producto(db, producto_data, current_user)

        assert result.nombre_producto == "Leche"
        assert result.cantidad == 2
        assert result.precio_estimado == 1.5
        assert lista.total_estimado == 3.0

        producto_repo.create.assert_called_once()
        lista_repo.save.assert_called_once()


def test_create_producto_lista_not_found(db, current_user):
    producto_data = ProductoListaCreate(
        nombre_producto="Leche",
        cantidad=2,
        unidad_medida="litros",
        supermercado="Mercadona",
        precio_estimado=1.5,
        lista_id=99
    )

    with patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo:
        lista_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            ProductoListaService.create_producto(db, producto_data, current_user)

        assert exc.value.status_code == 404
        assert exc.value.detail == "Lista no encontrada"


def test_create_producto_forbidden_if_lista_not_owned(db, current_user, lista):
    lista.usuario_id = 999

    producto_data = ProductoListaCreate(
        nombre_producto="Leche",
        cantidad=2,
        unidad_medida="litros",
        supermercado="Mercadona",
        precio_estimado=1.5,
        lista_id=1
    )

    with patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo:
        lista_repo.get_by_id.return_value = lista

        with pytest.raises(HTTPException) as exc:
            ProductoListaService.create_producto(db, producto_data, current_user)

        assert exc.value.status_code == 403
        assert exc.value.detail == "No tienes permiso para modificar esta lista"


def test_get_productos_by_lista_success(db, current_user, lista, producto):
    with patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo, \
         patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo:

        lista_repo.get_by_id.return_value = lista
        producto_repo.get_by_lista_id.return_value = [producto]

        result = ProductoListaService.get_productos_by_lista(db, 1, current_user)

        assert len(result) == 1
        assert result[0].nombre_producto == "Leche"


def test_get_producto_by_id_success(db, current_user, lista, producto):
    with patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo, \
         patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo:

        producto_repo.get_by_id.return_value = producto
        lista_repo.get_by_id.return_value = lista

        result = ProductoListaService.get_producto_by_id(db, 1, current_user)

        assert result.id_producto_lista == 1
        assert result.nombre_producto == "Leche"


def test_get_producto_by_id_not_found(db, current_user):
    with patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo:
        producto_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            ProductoListaService.get_producto_by_id(db, 99, current_user)

        assert exc.value.status_code == 404
        assert exc.value.detail == "Producto no encontrado"


def test_update_producto_success_recalculates_total(db, current_user, lista, producto):
    update_data = ProductoListaUpdate(
        cantidad=3,
        precio_estimado=2.0
    )

    productos_lista = [producto]

    with patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo, \
         patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo:

        producto_repo.get_by_id.return_value = producto
        producto_repo.save.return_value = producto
        producto_repo.get_by_lista_id.return_value = productos_lista
        lista_repo.get_by_id.return_value = lista
        lista_repo.save.return_value = lista

        result = ProductoListaService.update_producto(
            db,
            1,
            update_data,
            current_user
        )

        assert result.cantidad == 3
        assert result.precio_estimado == 2.0
        assert lista.total_estimado == 6.0

        producto_repo.save.assert_called_once()
        lista_repo.save.assert_called_once()


def test_delete_producto_success_recalculates_total(db, current_user, lista, producto):
    producto_restante = ProductoLista()
    producto_restante.id_producto_lista = 2
    producto_restante.nombre_producto = "Pan"
    producto_restante.cantidad = 1
    producto_restante.precio_estimado = 0.8
    producto_restante.lista_id = 1

    with patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo, \
         patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo:

        producto_repo.get_by_id.return_value = producto
        producto_repo.get_by_lista_id.return_value = [producto_restante]
        lista_repo.get_by_id.return_value = lista
        lista_repo.save.return_value = lista

        ProductoListaService.delete_producto(db, 1, current_user)

        producto_repo.delete.assert_called_once_with(db, producto)
        assert lista.total_estimado == 0.8
        lista_repo.save.assert_called_once()


def test_recalcular_total_lista_with_multiple_products(db, lista):
    producto_1 = ProductoLista()
    producto_1.cantidad = 2
    producto_1.precio_estimado = 1.5

    producto_2 = ProductoLista()
    producto_2.cantidad = 3
    producto_2.precio_estimado = 2.0

    with patch("app.services.producto_lista_service.ListaCompraRepository") as lista_repo, \
         patch("app.services.producto_lista_service.ProductoListaRepository") as producto_repo:

        lista_repo.get_by_id.return_value = lista
        producto_repo.get_by_lista_id.return_value = [producto_1, producto_2]

        ProductoListaService._recalcular_total_lista(db, 1)

        assert lista.total_estimado == 9.0
        lista_repo.save.assert_called_once_with(db, lista)