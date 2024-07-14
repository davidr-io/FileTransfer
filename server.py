# David Rochester


import socket
from struct import pack, unpack
import os, hashlib, sys, logging, math
import struct


class FileTransferServer:
    def __init__(self, port, recv_length):
        self.logger = logging.getLogger("SERVER")
        self.handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
        self.logger.propagate = False
        self.logger.info("Initializing server...")

        # debug statement
        print("Starting server")
        # End of logger code

        # Create a directory to store received files
        if not os.path.exists("received_files"):
            os.makedirs("received_files")

        self.port = port
        self.recv_length = recv_length
        self.server_socket = None
        self.is_running = True


    def start(self):
      
        self.logger.info("Starting TCP server...")
        self.is_running = True

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCP socket obj
            self.server_socket.bind(('0.0.0.0', self.port))                         # bind to all available interfaces
            self.server_socket.listen(5)
            self.server_socket.settimeout(1)
            self.logger.info(f"Server listening on {self.port}")


            self.is_running = True
        except OSError as e:
            self.logger.error(e)
            return False

        return self.is_running
      

    def write_file(self, filename, data):
        
        with open(os.path.join("received_files", filename), "wb") as file:
            file.write(data)


    def run(self):
        
        while self.is_running:
            try:
                self.logger.info("Attempting to accept connection...")
                client_socket, client_address = self.server_socket.accept()         # accept new client connection
                self.logger.info(f"Accepted connection from {client_address}")

                while self.is_running:
                    try:
                        data = client_socket.recv(self.recv_length)                 # accept data no longer than recv_length
                        if not data:
                            break

                        filename, file_size, chunk_size, checksum_length = self.unpack_transfer_request_message(data)       # attempt to decode and strip data received
                        self.logger.info(f"Received transfer request for file: {filename.decode('utf-8')}, size: {file_size}")

                        client_socket.sendall(self.pack_ack_message(0))                                                     # send ACK with chunk number 0
                        file_data = self.receive_file(client_socket, file_size, chunk_size, checksum_length)
                        
                        if file_data:
                            self.write_file(filename.decode('utf-8'), file_data)
                            self.logger.info(f"File {filename.decode('utf-8')} received and saved")
                            print("File saved")
                    except TimeoutError:
                        continue
                    except OSError as e:
                        self.logger.error(f"OSError: {e}")
                        self.shutdown()
                    except Exception as e:
                        self.logger.error(f"Error: {e}")
                        self.shutdown()
                client_socket.close()
            except TimeoutError:
                continue
            except OSError as e:
                self.logger.error(f"OSError: {e}")
            except Exception as e:
                self.logger.error(f"Exception: {e}")


    def receive_file(self, conn, file_size, chunk_size, checksum_length):
        
        received_data = b''
        remaining_size = file_size

        while remaining_size > 0:
            try:

                request_size = min(chunk_size, remaining_size)                                         # get size of next chunk to request
                chunk_number, chunk_data = self.receive_chunk(conn, request_size, checksum_length)     # get chunk if available
                
                if chunk_number == -1 or chunk_data is None:                                            
                    self.logger.error("Client disconnected during file transfer")
                    return None

                received_data += chunk_data                                 # concat chunk onto recieved data, decrement remaining size
                remaining_size -= len(chunk_data)

                ack_message = self.pack_ack_message(chunk_number)           # pack ack message
                conn.sendall(ack_message)

            except Exception as e:
                self.logger.error(f"Exception while receiving file: {e}")
                return None

        return received_data

    def receive_chunk(self, conn, chunk_size, checksum_length):
      
        try:
            chunk_number_bytes = conn.recv(4)
            if not chunk_number_bytes:
                return -1, None

            chunk_number = int.from_bytes(chunk_number_bytes, byteorder='big')      # parse chunk number 

            chunk_data = b''
            remaining_size = chunk_size

            while remaining_size > 0:                               # keep accepting chunk data in parts until we reach chunk_size
                recv_size = min(self.recv_length, remaining_size)
                part = conn.recv(recv_size)                         # part of chunk is recv_size 
                if not part:
                    return -1, None
                chunk_data += part                                  # add part to the saved chunk_data
                remaining_size -= len(part)                         # decrement remaining_size

            checksum = conn.recv(checksum_length)
            if not checksum:
                return -1, None

            combined_data = chunk_number_bytes + chunk_data
            our_checksum = self.compute_hash(combined_data, checksum_length)        # generate checksum using our data

            if checksum == our_checksum:
                return chunk_number + 1, chunk_data
            else:
                self.logger.error("Checksum mismatch")
                return chunk_number, None

        except Exception as e:
            self.logger.error(f"Exception while receiving chunk: {e}")
            return -1, None
        

    def unpack_transfer_request_message(self, bytes):
        
        filename_length = struct.unpack_from('!H', bytes, 0)[0]        # unpack filename_length
        offset = 2

        filename = struct.unpack_from(f'!{filename_length}s', bytes, offset)[0]    # unpack filename
        offset += filename_length

        file_size, chunk_size, checksum_length = struct.unpack_from('!IHB', bytes, offset)          # unpack file size, chunk size, and checksum len

        return filename, file_size, chunk_size, checksum_length


    def pack_ack_message(self, next_chunk_number):
        
        ack_message = struct.pack('!BI', 0, next_chunk_number)
        return ack_message


    def compute_hash(self, data, hash_length):
       
        hash_value = hashlib.shake_128()
        hash_value.update(data)
        return hash_value.digest(hash_length)



    def shutdown(self):
        
        self.logger.info('Server is shutting down...')

        self.is_running = False
    

        if self.server_socket:                  # if socket is open
            try:
                self.server_socket.close()
                self.logger.info('Server socket closed.')
            except Exception as e:
                self.logger.error(f'Error closing server socket: {e}')
        
        self.logger.removeHandler(self.handler)


if __name__ == "__main__":
    server = FileTransferServer(3001, 1024)
    if server.start():
        server.run()
