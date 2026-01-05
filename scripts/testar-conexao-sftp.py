import paramiko

# Configurações
hostname = 'localhost'
port = 2222
username = 'caixagis'
password = 'caixagis123'

# Conectar
transport = paramiko.Transport((hostname, port))
transport.connect(username=username, password=password)
sftp = paramiko.SFTPClient.from_transport(transport)

# Listar arquivos
print("Arquivos em /upload:")
print(sftp.listdir('/upload'))

# Upload de arquivo
# sftp.put('local_file.txt', '/upload/remote_file.txt')

# Download de arquivo
# sftp.get('/download/remote_file.txt', 'local_file.txt')

# Fechar conexão
sftp.close()
transport.close()