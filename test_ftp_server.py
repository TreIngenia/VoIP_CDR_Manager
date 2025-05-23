#!/usr/bin/env python3
"""
Script per avviare un server FTP di test locale
Richiede: pip install pyftpdlib
"""

import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    # Crea directory per il server FTP
    ftp_dir = os.path.join(os.getcwd(), 'ftp_test_data')
    os.makedirs(ftp_dir, exist_ok=True)
    
    # Crea alcuni file di test
    test_files = [
        'report_2025_01.csv',
        'report_2025_02.csv',
        'data_export.xlsx',
        'monthly_stats.txt'
    ]
    
    for filename in test_files:
        filepath = os.path.join(ftp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(f'Test data for {filename}\nGenerated for testing purposes\n')
    
    # Configura autorizzatore
    authorizer = DummyAuthorizer()
    authorizer.add_user("testuser", "testpass", ftp_dir, perm="elradfmw")
    authorizer.add_anonymous(ftp_dir)
    
    # Configura handler
    handler = FTPHandler
    handler.authorizer = authorizer
    
    # Avvia server
    server = FTPServer(("127.0.0.1", 21), handler)
    
    print("Server FTP di test avviato su localhost:21")
    print("Username: testuser")
    print("Password: testpass")
    print(f"Directory: {ftp_dir}")
    print("Premi Ctrl+C per fermare il server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer FTP fermato")

if __name__ == "__main__":
    main()
