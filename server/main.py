import asyncio
import logging
import os
import sys

# Ensure server folder is on PATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.gameserver import GameServer
from server.web_admin import WebAdminServer
from server.web_registration import WebRegistrationServer

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Main")

import threading
from server.gui_app import ModernServerGUI, ServerGUIApp, start_gui_app
import tkinter as tk

from server.item_mall import ItemMallServer

async def run_server_stack(server, web_admin, web_reg, item_mall_server):
    await asyncio.gather(
        server.run(host="0.0.0.0", port=6414),
        web_admin.start(host="0.0.0.0", port=8080),
        web_reg.start(host="0.0.0.0", port=8081),
        item_mall_server.start(host="0.0.0.0")
    )

def start_async_loop(loop, server, web_admin, web_reg, item_mall_server):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_server_stack(server, web_admin, web_reg, item_mall_server))

def main():
    logger.info("Initializing Wonderland Online Private Server...")

    # Initialize Game Server on port 6414 with absolute paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "wlo_server.db")
    static_db_path = os.path.join(base_dir, "server", "ServerDataBase.db")
    server = GameServer(db_path=db_path, static_db_path=static_db_path)

    # Initialize Web Admin Server on port 8080
    web_admin = WebAdminServer(server)

    # Initialize Web Registration Server on port 8081
    web_reg = WebRegistrationServer(db_path=db_path)

    # Initialize Dedicated Item Mall TCP Server on port 6416
    item_mall_server = ItemMallServer(port=6416)

    # Check CLI arguments: default launches Desktop GUI unless --headless / --cli specified
    is_headless = "--headless" in sys.argv or "--cli" in sys.argv or "--nogui" in sys.argv

    if is_headless:
        logger.info("Starting in Headless Console mode...")
        try:
            asyncio.run(run_server_stack(server, web_admin, web_reg, item_mall_server))
        except KeyboardInterrupt:
            logger.info("Server shut down by keyboard interrupt.")
    else:
        logger.info("Starting in Full Desktop GUI mode (C# MainForm1 & Character Editor Suite)...")
        # Run server network stack in dedicated background thread
        server_loop = asyncio.new_event_loop()
        server_thread = threading.Thread(target=start_async_loop, args=(server_loop, server, web_admin, web_reg, item_mall_server), daemon=True)
        server_thread.start()

        # Run Desktop GUI in main thread
        try:
            start_gui_app(game_server=server, db_path=db_path)
        except Exception as ex:
            logger.error(f"GUI Error: {ex}")

if __name__ == "__main__":
    main()
