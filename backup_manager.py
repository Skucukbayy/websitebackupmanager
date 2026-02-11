import os
import stat
import socket
import ftplib
import paramiko
import logging
from datetime import datetime
from time_utils import get_now
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
            self.sftp = None
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
    
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
            timestamp = get_now().strftime('%Y%m%d_%H%M%S')
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
    """Handle FTP/FTPS based backups"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ftp = None
        self.use_tls = False
        self.ftps_error = None  # Store FTPS error for debugging
    
    def connect(self) -> Tuple[bool, str]:
        """Establish FTP/FTPS connection - FTPS first, then plain FTP only if server allows"""
        # Try FTPS first
        success, message = self._connect_ftps()
        if success:
            return success, message
        
        # Store FTPS error for debugging
        self.ftps_error = message
        logger.warning(f"FTPS bağlantısı başarısız: {message}")
        
        # Only try plain FTP if FTPS failed with connection/timeout error
        # Don't try plain FTP if server explicitly requires TLS
        if any(x in message.lower() for x in ['421', 'tls', 'ssl', 'secure', 'cleartext']):
            logger.error("Sunucu TLS gerektiriyor ama FTPS bağlantısı kurulamadı")
            return False, f"FTPS bağlantısı başarısız: {message}"
        
        # Try plain FTP as fallback
        logger.info("FTPS başarısız, normal FTP deneniyor...")
        return self._connect_plain_ftp()
    
    def _connect_ftps(self) -> Tuple[bool, str]:
        """Try to connect with FTP over TLS (Explicit FTPS)"""
        try:
            logger.info(f"FTPS (Explicit TLS) bağlanıyor: {self.host}:{self.port}")
            
            # Create SSL context with strong settings
            import ssl
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # Accept self-signed certificates
            # Set minimum TLS version to 1.2 for security
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            # Custom FTP_TLS class that reuses SSL session for data connections
            # This is required by many FTP servers for security
            class ReusedSessionFTP_TLS(ftplib.FTP_TLS):
                """FTP_TLS subclass that reuses the session for data connections"""
                def ntransfercmd(self, cmd, rest=None):
                    conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
                    if self._prot_p:
                        conn = self.context.wrap_socket(
                            conn, 
                            server_hostname=self.host,
                            session=self.sock.session  # Reuse the control connection's session
                        )
                    return conn, size
            
            self.ftp = ReusedSessionFTP_TLS(context=context)
            self.ftp.encoding = 'utf-8'
            
            # Connect first
            logger.info(f"Sunucuya bağlanılıyor: {self.host}:{self.port}")
            self.ftp.connect(self.host, self.port, timeout=60)
            
            # Immediately upgrade to TLS - this sends AUTH TLS command
            logger.info("TLS şifreleme başlatılıyor (AUTH TLS)...")
            self.ftp.auth()
            
            # Login after TLS is established
            logger.info(f"FTPS giriş yapılıyor: {self.username}")
            self.ftp.login(self.username, self.password)
            
            # Switch to secure data connection (PROT P)
            logger.info("Güvenli veri bağlantısı aktif ediliyor (PROT P)...")
            self.ftp.prot_p()
            self.ftp.set_pasv(True)
            self.use_tls = True
            
            welcome = self.ftp.getwelcome()
            logger.info(f"FTPS bağlantısı başarılı: {welcome}")
            
            return True, f"Güvenli bağlantı başarılı (FTPS/TLS): {welcome}"
        except ftplib.error_perm as e:
            error_msg = f"FTPS yetki hatası: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except ftplib.error_temp as e:
            error_msg = f"FTPS geçici hata: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except ssl.SSLError as e:
            error_msg = f"SSL hatası: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"FTPS bağlantı hatası: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _connect_plain_ftp(self) -> Tuple[bool, str]:
        """Try to connect with plain FTP (no encryption)"""
        try:
            logger.info(f"Normal FTP bağlanıyor: {self.host}:{self.port}")
            self.ftp = ftplib.FTP()
            self.ftp.connect(self.host, self.port, timeout=60)
            logger.info(f"FTP giriş yapılıyor: {self.username}")
            self.ftp.login(self.username, self.password)
            self.ftp.set_pasv(True)
            self.use_tls = False
            
            welcome = self.ftp.getwelcome()
            logger.info(f"FTP bağlantısı başarılı: {welcome}")
            
            return True, f"Bağlantı başarılı: {welcome}"
        except ftplib.error_perm as e:
            error_msg = f"FTP yetki hatası: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except ftplib.error_temp as e:
            # This is the TLS required error
            error_msg = f"FTP sunucusu TLS gerektiriyor: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except socket.timeout:
            error_msg = f"FTP bağlantı zaman aşımı - sunucu yanıt vermiyor: {self.host}:{self.port}"
            logger.error(error_msg)
            return False, error_msg
        except socket.gaierror as e:
            error_msg = f"DNS çözümleme hatası - host bulunamadı: {self.host} - {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except ConnectionRefusedError:
            error_msg = f"Bağlantı reddedildi - FTP port ({self.port}) kapalı olabilir: {self.host}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"FTP bağlantı hatası: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
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
            self.ftp = None
            self.use_tls = False
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test FTP connection"""
        success, message = self.connect()
        if success:
            # Try to list root directory as additional test
            try:
                self.ftp.pwd()
                self.disconnect()
                return True, message
            except Exception as e:
                self.disconnect()
                return False, f"Bağlantı başarılı ama dizin erişimi başarısız: {str(e)}"
        return success, message
    
    def _parse_list_line(self, line: str) -> Tuple[str, bool]:
        """
        Parse FTP LIST output line to extract filename and is_directory flag.
        Handles both Unix and Windows FTP server formats.
        Returns: (filename, is_directory) or (None, False) if parsing fails
        """
        try:
            # Unix format: drwxr-xr-x 2 user group 4096 Jan 26 2024 dirname
            parts = line.split(None, 8)
            if len(parts) >= 9:
                permissions = parts[0]
                filename = parts[8]
                if filename in ['.', '..']:
                    return None, False
                is_dir = permissions.startswith('d')
                return filename, is_dir
            
            # Windows format: 01-26-24 08:30PM <DIR> dirname
            # or: 01-26-24 08:30PM 1234 filename
            parts = line.split(None)
            if len(parts) >= 4:
                # Check for Windows <DIR> format
                if '<DIR>' in line:
                    dir_idx = parts.index('<DIR>')
                    filename = ' '.join(parts[dir_idx + 1:])
                    if filename in ['.', '..']:
                        return None, False
                    return filename, True
                else:
                    # It's a file (has size instead of <DIR>)
                    filename = parts[-1]
                    if filename in ['.', '..']:
                        return None, False
                    return filename, False
        except Exception as e:
            logger.warning(f"FTP LIST satırı parse edilemedi: {line} - {e}")
        
        return None, False
    
    def download_directory(self, remote_path: str, local_path: str,
                          progress_callback=None) -> Tuple[int, int]:
        """
        Recursively download a directory via FTP using absolute paths.
        Does NOT use cwd() to avoid directory state corruption.
        Returns: (total_files, total_bytes)
        """
        total_files = 0
        total_bytes = 0
        
        os.makedirs(local_path, exist_ok=True)
        
        # Try MLSD first (more reliable), fallback to LIST
        # Use absolute path instead of cwd()
        items = []
        
        try:
            mlsd_items = list(self.ftp.mlsd(remote_path))
            for name, facts in mlsd_items:
                if name in ['.', '..']:
                    continue
                is_dir = facts.get('type') == 'dir'
                items.append((name, is_dir))
            logger.info(f"MLSD kullanıldı ({remote_path}), {len(items)} öğe bulundu")
        except:
            # MLSD not supported, use LIST with absolute path
            logger.info(f"MLSD desteklenmiyor, LIST kullanılacak: {remote_path}")
            
            # We need to cwd for LIST, but we'll restore it after
            try:
                original_dir = self.ftp.pwd()
            except:
                original_dir = '/'
            
            try:
                self.ftp.cwd(remote_path)
            except ftplib.error_perm as e:
                logger.error(f"FTP dizine erişilemiyor {remote_path}: {e}")
                return total_files, total_bytes
            
            lines = []
            try:
                self.ftp.retrlines('LIST', lines.append)
            except Exception as e:
                logger.error(f"LIST başarısız {remote_path}: {e}")
                # Restore original directory before returning
                try:
                    self.ftp.cwd(original_dir)
                except:
                    pass
                return total_files, total_bytes
            
            for line in lines:
                filename, is_dir = self._parse_list_line(line)
                if filename:
                    items.append((filename, is_dir))
            
            # Restore original directory after LIST
            try:
                self.ftp.cwd(original_dir)
            except:
                pass
            
            logger.info(f"LIST kullanıldı ({remote_path}), {len(items)} öğe bulundu")
        
        for filename, is_dir in items:
            remote_item_path = f"{remote_path}/{filename}"
            local_item_path = os.path.join(local_path, filename)
            
            try:
                if is_dir:
                    # Directory - recurse (no cwd needed, uses absolute paths)
                    files, bytes_downloaded = self.download_directory(
                        remote_item_path, local_item_path, progress_callback
                    )
                    total_files += files
                    total_bytes += bytes_downloaded
                else:
                    # File - download using absolute path
                    with open(local_item_path, 'wb') as f:
                        self.ftp.retrbinary(f'RETR {remote_item_path}', f.write)
                    
                    file_size = os.path.getsize(local_item_path)
                    total_files += 1
                    total_bytes += file_size
                    
                    if progress_callback:
                        progress_callback(filename, file_size)
                    
                    logger.debug(f"İndirildi: {remote_item_path} ({file_size} bytes)")
                        
            except Exception as e:
                logger.error(f"FTP indirme hatası {remote_item_path}: {type(e).__name__}: {e}")
                continue
        
        return total_files, total_bytes
    
    def backup(self, remote_path: str, local_backup_path: str,
               progress_callback=None) -> Tuple[bool, str, int, int]:
        """
        Perform full backup
        Returns: (success, message, file_count, total_bytes)
        """
        logger.info(f"FTP yedekleme başlatılıyor: {self.host}:{self.port} - {remote_path}")
        
        success, message = self.connect()
        if not success:
            logger.error(f"FTP bağlantısı kurulamadı: {message}")
            return False, message, 0, 0
        
        try:
            # 1. Validate Remote Path (use nlst instead of cwd to avoid state change)
            try:
                self.ftp.nlst(remote_path)
                logger.info(f"Uzak dizin doğrulandı: {remote_path}")
            except ftplib.error_perm as e:
                raise Exception(f"Uzak yol '{remote_path}' mevcut değil veya erişim izni yok: {e}")
            
            # 2. Validate Local Path Writable
            if os.path.exists(local_backup_path) and not os.access(local_backup_path, os.W_OK):
                raise Exception(f"Yerel yedekleme yolu '{local_backup_path}' yazılabilir değil")

            # Create timestamped backup folder
            timestamp = get_now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(local_backup_path, f'backup_{timestamp}')
            
            os.makedirs(local_backup_path, exist_ok=True)
            logger.info(f"Yedekleme dizini oluşturuldu: {backup_dir}")
            
            file_count, total_bytes = self.download_directory(
                remote_path, backup_dir, progress_callback
            )
            
            logger.info(f"FTP yedekleme tamamlandı: {file_count} dosya, {total_bytes} bytes")
            return True, backup_dir, file_count, total_bytes
            
        except Exception as e:
            error_msg = f"Yedekleme hatası: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, 0, 0
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
