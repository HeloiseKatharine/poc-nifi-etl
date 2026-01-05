import paramiko

hostname = 'localhost'
port = 2222
username = 'caixagis'
password = 'caixagis123'

transport = paramiko.Transport((hostname, port))
transport.connect(username=username, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)

#print("Arquivos em /upload:")
# print(sftp.listdir('/upload'))


# Download de arquivo
# sftp.get('/download/remote_file.txt', 'local_file.txt')

sftp.close()
transport.close()