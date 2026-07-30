import asyncio
import aiomysql

async def main():
    conn = await aiomysql.connect(
        host="10.128.15.93",
        port=3306,
        user="root",
        password="Rzx@1218",
        db="jeecg_adms_cloud",
        charset="utf8mb4",
        autocommit=True,
    )
    print("CONNECT_OK")
    conn.close()

asyncio.run(main())