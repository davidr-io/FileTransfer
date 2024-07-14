# David Rochester

import socket
from struct import pack, unpack
import os, time, sys, logging, hashlib, math
import struct


class FileTransferClient:
    def __init__(self, host, port, chunk_size=32768, hash_length=8):
        
        self.logger = logging.getLogger("CLIENT")
        self.handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
        self.logger.propagate = False
        self.logger.info("Initializing client...")
        # End of logger code

        self.host = host
        self.port = port
        self.chunk_size = chunk_size
        self.hash_length = hash_length

        self.client_socket = None

    def start(self):
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # tcp socket obj
            
            self.client_socket.connect((self.host, self.port))  # connect to tcp server
            self.logger.info("Successfully connected to the server.")

            #Debug statement
            if self.client_socket:
                print("Connected to server")
            
            return True
        except OSError as e:
            self.logger.error(f"Failed to connect to the server: {e}")
            return False

    def read_file(self, filepath):
        
        with open(filepath, "rb") as file:
            data = file.read()
            return data
        

    def send_file(self, filepath):
        
        try:

            with open(filepath, 'rb') as file:          # open file for reading
                file_data = file.read()
            

            filename = filepath.split('/')[-1]          # get the file parameters
            file_size = len(file_data)
            chunk_size = self.chunk_size
            checksum_length = self.hash_length

            transfer_request_message = self.pack_transfer_request_message(filename, file_size, chunk_size, checksum_length)     # send file transfer request to the server
            self.client_socket.sendall(transfer_request_message)
            
            
            ack_message = self.client_socket.recv(5)                                 # recv 5 bytes from server, 1 for ACK and 4 for unsinged int chunk_num
            ack_type, next_chunk_number = self.unpack_ack_message(ack_message)       # unpack response from server


            while next_chunk_number * chunk_size < file_size:                       # repeat until file is transferred completely
                start = next_chunk_number * chunk_size
                end = start + chunk_size
                chunk_data = file_data[start:end]

                file_chunk_message = self.pack_file_chunk(next_chunk_number, chunk_data)    # pack and send file chunk
                self.client_socket.sendall(file_chunk_message)

                ack_message = self.client_socket.recv(5)                                # get ACK from teh server
                ack_type, next_chunk_number = self.unpack_ack_message(ack_message)      # unpack ACK response 

            self.logger.info("File transfer completed successfully.")
            return True

        except TimeoutError as e:
            self.logger.error(f"Timeout error: {e}")
        except ConnectionResetError as e:
            self.logger.error(f"Connection reset error: {e}")
        except ConnectionAbortedError as e:
            self.logger.error(f"Connection aborted error: {e}")
        except OSError as e:
            self.logger.error(f"OS error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        
        return False
            
    
    def pack_transfer_request_message(self, filename, file_size, chunk_size, checksum_length):
        
        filename_bytes = filename.encode('utf-8')       # encode file name into bytes
        filename_length = len(filename_bytes)

        packed_message = struct.pack(f'!H{filename_length}sIHB',        # pack data 
                                    filename_length,
                                    filename_bytes,
                                    file_size,
                                    chunk_size,
                                    checksum_length)

        return packed_message

    def pack_file_chunk(self, chunk_number, chunk_bytes):
        
        packed_data = struct.pack('!I', chunk_number) + chunk_bytes
        checksum = self.compute_hash(packed_data)               # get checksum
        packed_data_with_checksum = packed_data + checksum      # concatenate checksum onto packed data
        return packed_data_with_checksum


    def unpack_ack_message(self, bytes):
        
        ACK_type, next_chunk_number = struct.unpack('!BI', bytes)
        return ACK_type, next_chunk_number

    def compute_hash(self, data):
    
        hash_value = hashlib.shake_128()
        hash_value.update(data)
        return hash_value.digest(self.hash_length)



    def shutdown(self):
        self.logger.info("Client is shutting down...")

        if self.client_socket:
            try:
                self.client_socket.close()
                self.logger.info("Client socket closed")
            except Exception as e:
                self.logger.error(f"Error: {e}")
        
        self.logger.removeHandler(self.handler)


if __name__ == "__main__":
    client = FileTransferClient("localhost", 3001)
    if client.start():
        client.send_file("source/test1.jpg")
        client.send_file("source/test2.jpg")
        client.shutdown()
