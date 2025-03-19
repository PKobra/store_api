from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pymongo
from bson import Decimal128
from store.db.mongo import db_client
from store.models.product import ProductModel
from store.schemas.product import ProductIn, ProductOut, ProductUpdate, ProductUpdateOut
from store.core.exceptions import NotFoundException


class ProductUsecase:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient = db_client.get()
        self.database: AsyncIOMotorDatabase = self.client.get_database()
        self.collection = self.database.get_collection("products")

    async def create(self, body: ProductIn) -> ProductOut:
        try:
            product_model = ProductModel(**body.model_dump())
            await self.collection.insert_one(product_model.model_dump())
            return ProductOut(**product_model.model_dump())
        except Exception as e:
            raise Exception(f"Erro ao criar produto: {str(e)}")

    async def get(self, id: UUID) -> ProductOut:
        result = await self.collection.find_one({"id": id})
        if not result:
            raise NotFoundException(message=f"Product not found with filter: {id}")
        return ProductOut(**result)

    async def query(
        self, 
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None
    ) -> List[ProductOut]:
        query = {}
        
        # Filtro de preço
        if min_price or max_price:
            query["price"] = {}
            if min_price:
                query["price"]["$gt"] = Decimal128(str(min_price))
            if max_price:
                query["price"]["$lt"] = Decimal128(str(max_price))

        return [ProductOut(**item) async for item in self.collection.find(query)]

    async def update(self, id: UUID, body: ProductUpdate) -> ProductUpdateOut:
        # Verifica existência
        existing = await self.collection.find_one({"id": id})
        if not existing:
            raise NotFoundException(message=f"Product not found with filter: {id}")

        # Atualiza o updated_at se não fornecido
        update_data = body.model_dump(exclude_none=True)
        if "updated_at" not in update_data:
            update_data["updated_at"] = datetime.utcnow()

        # Executa a atualização
        result = await self.collection.find_one_and_update(
            filter={"id": id},
            update={"$set": update_data},
            return_document=pymongo.ReturnDocument.AFTER,
        )
        return ProductUpdateOut(**result)

    async def delete(self, id: UUID) -> bool:
        product = await self.collection.find_one({"id": id})
        if not product:
            raise NotFoundException(message=f"Product not found with filter: {id}")
        
        result = await self.collection.delete_one({"id": id})
        return result.deleted_count > 0


product_usecase = ProductUsecase()