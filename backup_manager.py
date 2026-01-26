import os
import stat
import ftplib
import paramiko
import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class SSHBackupManager:
    """Handle SSH/SFTP based backups"""
    
    def __init__(self, host: str, port: int, username: str, 
                 password: Optional[str] = None, ssh_key_path: Optional[str] = None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh_key_path = ssh_key_path
        self.client = None
        self.sftp = None
    
    def connect(self) -> Tuple[bool, str]:
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': 30
            }
            
            if self.ssh_key_path and os.path.exists(self.ssh_key_path):
                connect_kwargs['key_filename'] = self.ssh_key_path
            elif self.password:
                connect_kwargs['password'] = self.password
            else:
                return False, "No authentication method provided"
            
            self.client.connect(**connect_kwargs)
            self.sftp = self.client.open_sftp()
            
            return True, "Connected successfully"
        except paramiko.AuthenticationException:
            return False, "Authentication failed. Check credentials."
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def disconnect(self):
        """Close SSH connection"""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
        if self.client:
            try:
                self.client.close()
            except:
                pass
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test SSH connection"""
        success, message = self.connect()
        if success:
            self.disconnect()
        return success, message
    
    def download_directory(self, remote_path: str, local_path: str, 
                          progress_callback=None) -> Tuple[int, int]:
        """
        Recursively download a directory via SFTP
        Returns: (total_files, total_bytes)
        """
        total_files = 0
        total_bytes = 0
        
        os.makedirs(local_path, exist_ok=True)
        
        try:
            items = self.sftp.listdir_attr(remote_path)
        except IOError as e:
            logger.error(f"Cannot list directory {remote_path}: {e}")
            # If we can't list it, we return what we have (0)
            # The caller should have verified existence beforehand for the root dir
            return total_files, total_bytes
        
        for item in items:
            remote_item_path = os.path.join(remote_path, item.filename).replace('\\', '/')
            local_item_path = os.path.join(local_path, item.filename)
            
            try:
                if stat.S_ISDIR(item.st_mode):
                    # Recursively download subdirectory
                    files, bytes_downloaded = self.download_directory(
                        remote_item_path, local_item_path, progress_callback
                    )
                    total_files += files
                    total_bytes += bytes_downloaded
                else:
                    # Download file
                    self.sftp.get(remote_item_path, local_item_path)
                    file_size = item.st_size
                    total_files += 1
                    total_bytes += file_size
                    
                    if progress_callback:
                        progress_callback(item.filename, file_size)
                        
            except Exception as e:
                logger.error(f"Error downloading {remote_item_path}: {e}")
                continue
        
        return total_files, total_bytes
    
    def backup(self, remote_path: str, local_backup_path: str, 
               progress_callback=None) -> Tuple[bool, str, int, int]:
        """
        Perform full backup
        Returns: (success, message, file_count, total_bytes)
        """
        success, message = self.connect()
        if not success:
            return False, message, 0, 0
        
        try:
            # 1. Validate Remote Path
            try:
                self.sftp.stat(remote_path)
            except IOError:
                 raise Exception(f"Remote path '{remote_path}' does not exist or is not accessible")

            # 2. Validate Local Path Writable
            if os.path.exists(local_backup_path) and not os.access(local_backup_path, os.W_OK):
                 raise Exception(f"Local backup path '{local_backup_path}' is not writable")
            
            # Create timestamped backup folder
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(local_backup_path, f'backup_{timestamp}')
            
            os.makedirs(local_backup_path, exist_ok=True)
            
            file_count, total_bytes = self.download_directory(
                remote_path, backup_dir, progress_callback
            )
            
            # If 0 files, check if it was really empty or if something failed silently
            if file_count == 0:
                try:
                    if not self.sftp.listdir(remote_path):
                        # Truly empty
                        pass
                except:
                     pass

            return True, backup_dir, file_count, total_bytes
            
        except Exception as e:
            return False, f"Backup error: {str(e)}", 0, 0
        finally:
            self.disconnect()


class FTPBackupManager:
    """Handle FTP based backups"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ftp = None
    
    def connect(self) -> Tuple[bool, str]:
        """Establish FTP connection"""
        try:
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=30)
            self.ftp.login(self.username, self.password)
            self.ftp.set_pasv(True)
            
            return True, "Connected successfully"
        except ftplib.error_perm as e:
            return False, f"FTP permission error: {str(e)}"
        except Exception as e:
            return False, f"FTP connection error: {str(e)}"
    
    def disconnect(self):
        """Close FTP connection"""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                try:
                    self.ftp.close()
                except:
                    pass
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test FTP connection"""
        success, message = self.connect()
        if success:
            self.disconnect()
        return success, message
    
    def download_directory(self, remote_path: str, local_path: str,
                          progress_callback=None) -> Tuple[int, int]:
        """
        Recursively download a directory via FTP
        Returns: (total_files, total_bytes)
        """
        total_files = 0
        total_bytes = 0
        
        os.makedirs(local_path, exist_ok=True)
        
        try:
            self.ftp.cwd(remote_path)
        except ftplib.error_perm:
            logger.error(f"Cannot change to directory {remote_path}")
            return total_files, total_bytes
        
        items = []
        try:
            self.ftp.retrlines('LIST', items.append)
        except Exception as e:
            logger.error(f"LIST failed for {remote_path}: {e}")
            return total_files, total_bytes
        
        for item in items:
            # Parsing LIST output is fragile, specifically across different servers
            # Best effort logic
            parts = item.split(None, 8)
            if len(parts) < 9:
                continue
                
            permissions = parts[0]
            filename = parts[8]
            
            if filename in ['.', '..']:
                continue
            
            remote_item_path = f"{remote_path}/{filename}"
            local_item_path = os.path.join(local_path, filename)
            
            try:
                if permissions.startswith('d'):
                    # Directory - recurse
                    files, bytes_downloaded = self.download_directory(
                        remote_item_path, local_item_path, progress_callback
                    )
                    total_files += files
                    total_bytes += bytes_downloaded
                    # Go back to parent directory because download_directory does cwd
                    self.ftp.cwd(remote_path)
                else:
                    # File - download
                    with open(local_item_path, 'wb') as f:
                        self.ftp.retrbinary(f'RETR {filename}', f.write)
                    
                    file_size = os.path.getsize(local_item_path)
                    total_files += 1
                    total_bytes += file_size
                    
                    if progress_callback:
                        progress_callback(filename, file_size)
                        
            except Exception as e:
                logger.error(f"Error downloading {remote_item_path}: {e}")
                continue
        
        return total_files, total_bytes
    
    def backup(self, remote_path: str, local_backup_path: str,
               progress_callback=None) -> Tuple[bool, str, int, int]:
        """
        Perform full backup
        Returns: (success, message, file_count, total_bytes)
        """
        success, message = self.connect()
        if not success:
            return False, message, 0, 0
        
        try:
            # 1. Validate Remote Path
            try:
                self.ftp.cwd(remote_path)
            except ftplib.error_perm:
                 raise Exception(f"Remote path '{remote_path}' does not exist or permission denied")
            
            # Reset CWD to root for safety before starting recursion logic if needed, 
            # or rely on download_directory to set it.
            # download_directory expects to be able to cwd to it.

            # 2. Validate Local Path Writable
            if os.path.exists(local_backup_path) and not os.access(local_backup_path, os.W_OK):
                 raise Exception(f"Local backup path '{local_backup_path}' is not writable")

            # Create timestamped backup folder
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(local_backup_path, f'backup_{timestamp}')
            
            os.makedirs(local_backup_path, exist_ok=True)
            
            file_count, total_bytes = self.download_directory(
                remote_path, backup_dir, progress_callback
            )
            
            return True, backup_dir, file_count, total_bytes
            
        except Exception as e:
            return False, f"Backup error: {str(e)}", 0, 0
        finally:
            self.disconnect()


def get_backup_manager(protocol: str, host: str, port: int, username: str,
                       password: Optional[str] = None, ssh_key_path: Optional[str] = None):
    """Factory function to get appropriate backup manager"""
    if protocol.upper() == 'SSH':
        return SSHBackupManager(host, port, username, password, ssh_key_path)
    elif protocol.upper() == 'FTP':
        return FTPBackupManager(host, port, username, password)
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")
