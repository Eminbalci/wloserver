import os
import sqlite3
import struct
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PopulatePortals")

def is_visible_portal(name, dest_mapID):
    if dest_mapID == 58001:
        return False
    blacklist = ['左上', '左下', '右上', 'right', 'left', '右下', '大地图', '大地圖', '上岸']
    for b in blacklist:
        if b in name:
            return False
    if name and name[0].isdigit():
        return False
    return True

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eve_path = os.path.join(base_dir, "data", "eve.Emg")
    db_path = os.path.join(base_dir, "server", "ServerDataBase.db")

    if not os.path.exists(eve_path):
        logger.error(f"eve.Emg not found at {eve_path}")
        return

    logger.info(f"Reading {eve_path}...")
    with open(eve_path, "rb") as f:
        d = f.read()

    # Read entry length
    entrylen = struct.unpack_from("<I", d, 8)[0]
    logger.info(f"Found {entrylen} map entries in eve.Emg header.")

    ptr = 12
    maps = {}
    for i in range(entrylen):
        mapID, sceneID, dataptr, datalen = struct.unpack_from("<HHIH", d, ptr)
        ptr += 10
        maps[mapID] = {
            'mapID': mapID,
            'sceneID': sceneID,
            'dataptr': dataptr,
            'datalen': datalen
        }

    logger.info(f"Loaded {len(maps)} maps.")

    portals_to_insert = []
    destinations_to_insert = []

    for mapID, m in maps.items():
        # Category offsets are at dataptr + datalen - 44
        off_ptr = m['dataptr'] + m['datalen'] - 44
        if off_ptr + 44 > len(d):
            continue

        offsets = struct.unpack_from("<IIIIIIIIIII", d, off_ptr)
        warp_offset = offsets[6] # Warp category is the 7th offset (index 6)

        # Warp entries start at dataptr + warp_offset
        warp_ptr = m['dataptr'] + warp_offset
        if warp_ptr + 2 > len(d):
            continue

        elen = struct.unpack_from("<H", d, warp_ptr)[0]
        cur_ptr = warp_ptr + 2

        visible_idx = 1
        for w_idx in range(elen):
            if cur_ptr + 35 > len(d):
                break
            clickID = struct.unpack_from("<H", d, cur_ptr)[0]
            name_len = d[cur_ptr+2]
            name_bytes = d[cur_ptr+3 : cur_ptr+3+name_len]
            name = name_bytes.decode('cp950', errors='ignore').strip()
            dest_mapID = struct.unpack_from("<H", d, cur_ptr+22)[0]
            dest_x = struct.unpack_from("<I", d, cur_ptr+24)[0]
            dest_y = struct.unpack_from("<I", d, cur_ptr+28)[0]

            # All transitions must be in warp_destinations with clickID as destID
            destinations_to_insert.append((mapID, clickID, dest_mapID, dest_x, dest_y))
            
            # Visible portals get mapped in portals: portalID = visible_idx -> destID = clickID
            if is_visible_portal(name, dest_mapID):
                portals_to_insert.append((mapID, visible_idx, clickID))
                visible_idx += 1
            
            cur_ptr += 35

    logger.info(f"Extracted {len(portals_to_insert)} visible portals and {len(destinations_to_insert)} total warp destinations from eve.Emg.")

    # Open SQLite Database and write
    logger.info(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    try:
        # Recreate tables to be clean
        conn.execute("DROP TABLE IF EXISTS portals")
        conn.execute("DROP TABLE IF EXISTS warp_destinations")

        conn.execute("""
            CREATE TABLE portals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapID INTEGER NOT NULL,
                portalID INTEGER NOT NULL,
                destID INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE warp_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapID INTEGER NOT NULL,
                destID INTEGER NOT NULL,
                dstMap INTEGER NOT NULL,
                dstX INTEGER NOT NULL,
                dstY INTEGER NOT NULL
            )
        """)

        # Insert portals in bulk
        conn.executemany(
            "INSERT INTO portals (mapID, portalID, destID) VALUES (?, ?, ?)",
            portals_to_insert
        )
        # Insert warp destinations in bulk
        conn.executemany(
            "INSERT INTO warp_destinations (mapID, destID, dstMap, dstX, dstY) VALUES (?, ?, ?, ?, ?)",
            destinations_to_insert
        )

        conn.commit()
        logger.info(f"Database population completed successfully! Imported {len(portals_to_insert)} portals and {len(destinations_to_insert)} destinations.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to populate database: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
