import os
from Huffman_method.huffman import HuffmanTree
from Interfaces.decompress import DecompressorABC
from Huffman_method.const_byte import *


class Decompressor(DecompressorABC):
    def __init__(self, block_size=512):
        self.block_size = block_size
        self.version = 1

    def decompress(self, archive_file, out_path):
        with open(archive_file, 'rb') as file:
            first_bytes = file.read(36)
            type_compress = self.__check_magic_header(first_bytes)
        if type_compress == 0:
            self.__decompress__(archive_file, out_path)
        elif type_compress == 1:
            self.__decompress__(archive_file, out_path)

    def __decompress__(self, archive_file, out_path):
        name_dir = os.path.splitext(os.path.basename(archive_file))[0]
        out_path = str(os.path.join(out_path, name_dir))
        if not self.__is_file(out_path):
            os.makedirs(out_path, exist_ok=True)

        buffer = bytes()
        flag = 1
        path_out_file = ''
        current_tree = HuffmanTree()
        codec = None

        with open(archive_file, 'rb') as file:
            _ = file.read(36)
            while True:
                buffer += file.read(self.block_size)
                if not buffer:
                    break

                if flag == 1:
                    flag, current_tree, buffer = self.__read_tree(buffer)
                    if current_tree:
                        codec = current_tree.get_codec()
                if flag == 2:
                    flag, current_path, bits, buffer = self.__read_directory(buffer, current_tree)
                    if self.__is_file(out_path):
                        path_out_file = out_path
                    else:
                        path_out_file = os.path.join(out_path, current_path)
                if flag == 3:
                    flag, decoded_data, bits, buffer = self.__reed_data(bits, buffer, current_tree)
                    if self.__is_file(path_out_file) or decoded_data:
                        dir_path = os.path.dirname(path_out_file)
                        os.makedirs(dir_path, exist_ok=True)
                        if codec is None:
                            open_mode = 'ab'
                        else:
                            open_mode = 'a'
                        with open(path_out_file, open_mode) as out_file:
                            if codec:
                                out_file.write(decoded_data)
                            else:
                                out_file.write(decoded_data)
                    else:
                        os.makedirs(path_out_file, exist_ok=True)

    def __check_magic_header(self, block):
        len_magic_bytes = len(MAGIC_BYTES)
        len_all = len_magic_bytes + 32
        if len(block) >= len_all:
            if block[:len_magic_bytes] == MAGIC_BYTES:
                header = block[len(MAGIC_BYTES):len_all]
                current_version = int.from_bytes(header[:1], byteorder='big')
                type_compress = int.from_bytes(header[1:3], byteorder='big')

                if current_version <= self.version:
                    return type_compress
                else:
                    raise ValueError("Version decompress don't supported this archive")
            else:
                raise ValueError("Invalid identify archive format")

        return None

    @staticmethod
    def __read_tree(block):
        cookie_tree = block.find(MAGIC_COOKIE_TREE)
        if cookie_tree >= 0:
            serializable_tree = block[:cookie_tree]
            try:
                tree = HuffmanTree()
                tree.deserialize_from_string(serializable_tree)
                return 2, tree, block[cookie_tree + len(MAGIC_COOKIE_TREE):]
            except Exception as e:
                print(f"Failed to deserialize tree: {e}")

        return 1, None, block

    def __read_directory(self, block, tree):
        cookie_dir = block.find(MAGIC_COOKIE_DIR)
        if cookie_dir >= 0:
            path_dir = block[:cookie_dir]
            bits = self.__bytes_to_bits(path_dir)
            count = bits[-8:]
            decoded_path, other_bits = tree.decode(bits, int(count, 2))
            if tree.get_codec() is None:
                decoded_path = decoded_path.decode('utf-8')
            block = block[cookie_dir + len(MAGIC_COOKIE_DIR):]
            return 3, decoded_path, other_bits, block
        else:
            return 2, None, None, block

    def __reed_data(self, bits, block, tree):
        cookie_data = block.find(MAGIC_COOKIE_DATA)

        if cookie_data >= 0:
            last_data = block[:cookie_data]
            bits += self.__bytes_to_bits(last_data)
            count = bits[-8:]
            if count:
                decoded_data, other_bits = tree.decode(bits, int(count, 2))
            else:
                decoded_data, other_bits = tree.decode(bits)

            block = block[cookie_data + len(MAGIC_COOKIE_DATA):]
            return 1, decoded_data, other_bits, block
        else:
            bits += self.__bytes_to_bits(block)
            decoded_data, other_bits = tree.decode(bits)

            return 3, decoded_data, other_bits, bytes()

    @staticmethod
    def __bytes_to_bits(data):
        bits = ''.join(format(byte, '08b') for byte in data)
        return bits

    @staticmethod
    def __bits_to_bytes(bits, huffman_tree):
        decoded_chars = []
        current_bits = ''
        for bit in bits:
            current_bits += bit
            symbol = huffman_tree.decode(current_bits)
            if symbol is not None:
                decoded_chars.append(symbol)
                current_bits = ''
        decoded_data = ''.join(decoded_chars)
        return decoded_data, current_bits

    @staticmethod
    def __is_file(path):
        _, extension = os.path.splitext(path)
        if extension:
            return True
        else:
            return False
