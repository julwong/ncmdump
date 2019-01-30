# Modifier: Liang Lixin
# Thanks for nondanee
from __future__ import print_function
import traceback
import binascii
import struct
import base64
import json
import os
from Crypto.Cipher import AES
import mutagen

def dump(file_path):
    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")
    unpad = lambda s : s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]
    f = open(file_path,'rb')
    header = f.read(8)
    assert binascii.b2a_hex(header) == b'4354454e4644414d'
    f.seek(2, 1)
    key_length = f.read(4)
    key_length = struct.unpack('<I', bytes(key_length))[0]
    key_data = f.read(key_length)
    key_data_array = bytearray(key_data)
    for i in range (0,len(key_data_array)): key_data_array[i] ^= 0x64
    key_data = bytes(key_data_array)
    cryptor = AES.new(core_key, AES.MODE_ECB)
    key_data = unpad(cryptor.decrypt(key_data))[17:]
    key_length = len(key_data)
    key_data = bytearray(key_data)
    key_box = bytearray(range(256))
    c = 0
    last_byte = 0
    key_offset = 0
    for i in range(256):
        swap = key_box[i]
        c = (swap + last_byte + key_data[key_offset]) & 0xff
        key_offset += 1
        if key_offset >= key_length: key_offset = 0
        key_box[i] = key_box[c]
        key_box[c] = swap
        last_byte = c
    meta_length = f.read(4)
    meta_length = struct.unpack('<I', bytes(meta_length))[0]
    meta_data = f.read(meta_length)
    meta_data_array = bytearray(meta_data)
    for i in range(0,len(meta_data_array)): meta_data_array[i] ^= 0x63
    meta_data = bytes(meta_data_array)
    meta_data = base64.b64decode(meta_data[22:])
    cryptor = AES.new(meta_key, AES.MODE_ECB)
    meta_data = unpad(cryptor.decrypt(meta_data)).decode('utf-8')[6:]
    meta_data = json.loads(meta_data)
    print(json.dumps(meta_data, indent=2))
    crc32 = f.read(4)
    crc32 = struct.unpack('<I', bytes(crc32))[0]
    f.seek(5, 1)
    image_size = f.read(4)
    image_size = struct.unpack('<I', bytes(image_size))[0]
    print(image_size)
    image_data = f.read(image_size)
    thumb_file_path = os.path.splitext(file_path)[0] + '.thumb'
    if not os.path.exists(thumb_file_path): # create cover front picture
        with open(thumb_file_path, 'wb') as img:
            img.write(image_data)
    # file_name = meta_data['musicName'] + '.' + meta_data['format']
    # m = open(os.path.join(os.path.split(file_path)[0],file_name),'wb')
    new_file_path = os.path.splitext(file_path)[0] + '.' + meta_data['format']
    if os.path.exists(new_file_path): # skip
        print(new_file_path, 'already exists')
        return
    m = open(new_file_path,'wb')
    chunk = bytearray()
    while True:
        chunk = bytearray(f.read(0x8000))
        chunk_length = len(chunk)
        if not chunk:
            break
        for i in range(1,chunk_length+1):
            j = i & 0xff;
            chunk[i-1] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]
        m.write(chunk)
    m.close()
    f.close()
    # add tags
    m = mutagen.File(new_file_path)
    # {'tracktotal': ['12'], 'artist': ['KOKIA'], 'genre': ['J-Pop\r'], 'tracknumber': ['3'], 'title': ['Ave Maria'], 'date': ['2008'], 'album': ['The VOICE']}
    m['artist'] = [artist[0] for artist in meta_data['artist']]
    m['title'] = [meta_data['musicName']]
    m['album'] = [meta_data['album']]
    if meta_data['format'] == 'flac':
        pic = mutagen.flac.Picture()
        pic.data = image_data
        pic.type = mutagen.id3.PictureType.COVER_FRONT
        # require Pillow
        from PIL import Image
        im = Image.open(thumb_file_path)
        pic.mime =  im.get_format_mimetype()
        pic.width = im.width
        pic.height = im.height
        pic.depth = 16
        m.add_picture(pic)
    m.save()
    
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        for file_path in sys.argv[1:]:
            try:
                dump(file_path)
            except:
                traceback.print_exc()
    else:
        print("Usage: python ncmdump.py \"File Name\"")
