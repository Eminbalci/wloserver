import os
import struct

def parse_odd_fat(filepath):
    size = os.path.getsize(filepath)
    with open(filepath, 'rb') as f:
        f.seek(size - 2)
        count_bytes = f.read(2)
        file_count = struct.unpack('<H', count_bytes)[0]
        print(f"Total files in FAT: {file_count}")

        # Let's search for the first file "1001_bt01.ogg"
        chunk_size = 1024 * 1024
        f.seek(size - chunk_size)
        data = f.read(chunk_size)
        
        idx = data.find(b'\x0D1001_bt01.ogg\x00')
        if idx == -1:
            print("Could not find start of FAT")
            return
            
        print(f"FAT starts at chunk offset {idx}")
        
        fat_data = data[idx:-2] # exclude the last 2 bytes (file count)
        
        ptr = 0
        files = []
        try:
            for i in range(file_count):
                name_len = fat_data[ptr]
                ptr += 1
                
                name_bytes = fat_data[ptr:ptr+name_len]
                name = name_bytes.decode('ascii', errors='ignore')
                ptr += name_len
                
                # Now we have some padding and then 12 bytes of data (4 unknown, 4 offset, 4 size)
                # Let's find the start of the 12 bytes.
                # Actually, the data usually starts with $\x05\xfds which is `24 05 fd 73`
                # Let's just find `24 05 fd 73`
                magic_idx = fat_data.find(b'\x24\x05\xfd\x73', ptr)
                if magic_idx == -1:
                    print(f"Could not find magic bytes for file {i} {name}")
                    break
                
                ptr = magic_idx + 4
                offset = struct.unpack('<I', fat_data[ptr:ptr+4])[0]
                ptr += 4
                size_val = struct.unpack('<I', fat_data[ptr:ptr+4])[0]
                ptr += 4
                
                files.append({'name': name, 'offset': offset, 'size': size_val})
                
                # After size, there are maybe some bytes?
                # Actually, the next byte is the length of the next filename!
                # Let's see if ptr points to the length of the next filename.
                
            print(f"Successfully parsed {len(files)} files.")
            
            # Print some maps
            maps = [f for f in files if f['name'].endswith('.map')]
            print(f"Found {len(maps)} .map files")
            for m in maps[:10]:
                print(m)
                
        except Exception as e:
            print(f"Error at file {len(files)}: {e}")

if __name__ == '__main__':
    parse_odd_fat(r'C:\Users\muham\OneDrive\Masaüstü\WLRI\data\odd.dat')
