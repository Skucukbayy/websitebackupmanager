"""
Cloud Storage Integration Module
Supports Google Drive, OneDrive (Microsoft Graph), and Dropbox.
Each provider implements: authenticate, upload_file, list_folders, get_auth_url, handle_callback
"""
import os
import json
import logging
import zipfile
import tempfile
import requests as http_requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CloudStorageBase:
    """Base class for cloud storage providers"""
    
    PROVIDER = None
    
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
    
    def set_tokens(self, access_token, refresh_token=None, token_expiry=None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
    
    def is_token_expired(self):
        if not self.token_expiry:
            return True
        if isinstance(self.token_expiry, str):
            self.token_expiry = datetime.fromisoformat(self.token_expiry)
        return datetime.utcnow() >= self.token_expiry
    
    def get_auth_url(self, state=None):
        raise NotImplementedError
    
    def handle_callback(self, code):
        raise NotImplementedError
    
    def refresh_access_token(self):
        raise NotImplementedError
    
    def ensure_valid_token(self):
        if self.is_token_expired() and self.refresh_token:
            self.refresh_access_token()
    
    def list_folders(self, folder_id=None):
        raise NotImplementedError
    
    def upload_file(self, local_path, remote_folder_id, filename=None):
        raise NotImplementedError


class GoogleDriveManager(CloudStorageBase):
    """Google Drive API v3"""
    
    PROVIDER = 'google_drive'
    AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    API_BASE = 'https://www.googleapis.com'
    SCOPES = 'https://www.googleapis.com/auth/drive.file'
    
    def get_auth_url(self, state=None):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': self.SCOPES,
            'access_type': 'offline',
            'prompt': 'consent',
        }
        if state:
            params['state'] = state
        
        query = '&'.join(f'{k}={http_requests.utils.quote(str(v))}' for k, v in params.items())
        return f'{self.AUTH_URL}?{query}'
    
    def handle_callback(self, code):
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }
        resp = http_requests.post(self.TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        self.refresh_token = tokens.get('refresh_token', self.refresh_token)
        expires_in = tokens.get('expires_in', 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def refresh_access_token(self):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        resp = http_requests.post(self.TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        expires_in = tokens.get('expires_in', 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def list_folders(self, folder_id=None):
        self.ensure_valid_token()
        parent = folder_id or 'root'
        
        query = f"'{parent}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        params = {
            'q': query,
            'fields': 'files(id,name)',
            'orderBy': 'name',
            'pageSize': 100
        }
        
        resp = http_requests.get(
            f'{self.API_BASE}/drive/v3/files',
            headers=self._headers(),
            params=params
        )
        resp.raise_for_status()
        
        folders = resp.json().get('files', [])
        return [{'id': f['id'], 'name': f['name']} for f in folders]
    
    def upload_file(self, local_path, remote_folder_id, filename=None):
        self.ensure_valid_token()
        
        if not filename:
            filename = os.path.basename(local_path)
        
        file_size = os.path.getsize(local_path)
        
        # Step 1: Create resumable upload session
        metadata = {
            'name': filename,
            'parents': [remote_folder_id or 'root']
        }
        
        headers = {
            **self._headers(),
            'Content-Type': 'application/json; charset=UTF-8',
            'X-Upload-Content-Length': str(file_size)
        }
        
        resp = http_requests.post(
            f'{self.API_BASE}/upload/drive/v3/files?uploadType=resumable',
            headers=headers,
            json=metadata
        )
        resp.raise_for_status()
        upload_url = resp.headers.get('Location')
        
        # Step 2: Upload file content
        with open(local_path, 'rb') as f:
            resp = http_requests.put(
                upload_url,
                headers={'Content-Length': str(file_size)},
                data=f
            )
            resp.raise_for_status()
        
        result = resp.json()
        logger.info(f"Google Drive upload complete: {filename} -> {result.get('id')}")
        return result.get('id')


class OneDriveManager(CloudStorageBase):
    """Microsoft OneDrive via Graph API"""
    
    PROVIDER = 'onedrive'
    AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
    TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
    API_BASE = 'https://graph.microsoft.com/v1.0'
    SCOPES = 'Files.ReadWrite.All offline_access'
    
    def get_auth_url(self, state=None):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': self.SCOPES,
        }
        if state:
            params['state'] = state
        
        query = '&'.join(f'{k}={http_requests.utils.quote(str(v))}' for k, v in params.items())
        return f'{self.AUTH_URL}?{query}'
    
    def handle_callback(self, code):
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code',
            'scope': self.SCOPES
        }
        resp = http_requests.post(self.TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        self.refresh_token = tokens.get('refresh_token', self.refresh_token)
        expires_in = tokens.get('expires_in', 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def refresh_access_token(self):
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'scope': self.SCOPES
        }
        resp = http_requests.post(self.TOKEN_URL, data=data)
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        self.refresh_token = tokens.get('refresh_token', self.refresh_token)
        expires_in = tokens.get('expires_in', 3600)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def list_folders(self, folder_id=None):
        self.ensure_valid_token()
        
        if folder_id:
            url = f'{self.API_BASE}/me/drive/items/{folder_id}/children'
        else:
            url = f'{self.API_BASE}/me/drive/root/children'
        
        params = {
            '$filter': "folder ne null",
            '$select': 'id,name,folder',
            '$orderby': 'name',
            '$top': 100
        }
        
        resp = http_requests.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        
        items = resp.json().get('value', [])
        return [{'id': item['id'], 'name': item['name']} for item in items if 'folder' in item]
    
    def upload_file(self, local_path, remote_folder_id, filename=None):
        self.ensure_valid_token()
        
        if not filename:
            filename = os.path.basename(local_path)
        
        file_size = os.path.getsize(local_path)
        
        # For files > 4MB, use upload session
        if file_size > 4 * 1024 * 1024:
            return self._upload_large_file(local_path, remote_folder_id, filename, file_size)
        
        # Small file: direct upload
        if remote_folder_id:
            url = f'{self.API_BASE}/me/drive/items/{remote_folder_id}:/{filename}:/content'
        else:
            url = f'{self.API_BASE}/me/drive/root:/{filename}:/content'
        
        with open(local_path, 'rb') as f:
            resp = http_requests.put(
                url,
                headers={**self._headers(), 'Content-Type': 'application/octet-stream'},
                data=f
            )
            resp.raise_for_status()
        
        result = resp.json()
        logger.info(f"OneDrive upload complete: {filename} -> {result.get('id')}")
        return result.get('id')
    
    def _upload_large_file(self, local_path, remote_folder_id, filename, file_size):
        # Create upload session
        if remote_folder_id:
            url = f'{self.API_BASE}/me/drive/items/{remote_folder_id}:/{filename}:/createUploadSession'
        else:
            url = f'{self.API_BASE}/me/drive/root:/{filename}:/createUploadSession'
        
        resp = http_requests.post(url, headers=self._headers(), json={
            'item': {'name': filename}
        })
        resp.raise_for_status()
        upload_url = resp.json()['uploadUrl']
        
        # Upload in 10MB chunks
        chunk_size = 10 * 1024 * 1024
        with open(local_path, 'rb') as f:
            offset = 0
            while offset < file_size:
                chunk = f.read(chunk_size)
                end = offset + len(chunk) - 1
                
                headers = {
                    'Content-Range': f'bytes {offset}-{end}/{file_size}',
                    'Content-Length': str(len(chunk))
                }
                resp = http_requests.put(upload_url, headers=headers, data=chunk)
                
                if resp.status_code in (200, 201):
                    result = resp.json()
                    logger.info(f"OneDrive large upload complete: {filename}")
                    return result.get('id')
                elif resp.status_code == 202:
                    offset += len(chunk)
                else:
                    resp.raise_for_status()
        
        return None


class DropboxManager(CloudStorageBase):
    """Dropbox API v2"""
    
    PROVIDER = 'dropbox'
    AUTH_URL = 'https://www.dropbox.com/oauth2/authorize'
    TOKEN_URL = 'https://api.dropboxapi.com/oauth2/token'
    API_BASE = 'https://api.dropboxapi.com/2'
    CONTENT_BASE = 'https://content.dropboxapi.com/2'
    
    def get_auth_url(self, state=None):
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'token_access_type': 'offline',
        }
        if state:
            params['state'] = state
        
        query = '&'.join(f'{k}={http_requests.utils.quote(str(v))}' for k, v in params.items())
        return f'{self.AUTH_URL}?{query}'
    
    def handle_callback(self, code):
        data = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        resp = http_requests.post(
            self.TOKEN_URL,
            data=data,
            auth=(self.client_id, self.client_secret)
        )
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        self.refresh_token = tokens.get('refresh_token', self.refresh_token)
        expires_in = tokens.get('expires_in', 14400)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def refresh_access_token(self):
        data = {
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        resp = http_requests.post(
            self.TOKEN_URL,
            data=data,
            auth=(self.client_id, self.client_secret)
        )
        resp.raise_for_status()
        tokens = resp.json()
        
        self.access_token = tokens['access_token']
        expires_in = tokens.get('expires_in', 14400)
        self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return {
            'access_token': self.access_token,
            'token_expiry': self.token_expiry.isoformat()
        }
    
    def _headers(self):
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def list_folders(self, folder_id=None):
        self.ensure_valid_token()
        
        path = folder_id or ''
        
        resp = http_requests.post(
            f'{self.API_BASE}/files/list_folder',
            headers={**self._headers(), 'Content-Type': 'application/json'},
            json={'path': path, 'include_non_downloadable_files': False}
        )
        resp.raise_for_status()
        
        entries = resp.json().get('entries', [])
        folders = [
            {'id': e['path_lower'], 'name': e['name']}
            for e in entries if e['.tag'] == 'folder'
        ]
        return folders
    
    def upload_file(self, local_path, remote_folder_id, filename=None):
        self.ensure_valid_token()
        
        if not filename:
            filename = os.path.basename(local_path)
        
        folder_path = remote_folder_id or ''
        dest_path = f'{folder_path}/{filename}'
        
        file_size = os.path.getsize(local_path)
        
        # For files > 150MB, use upload session
        if file_size > 150 * 1024 * 1024:
            return self._upload_large_file(local_path, dest_path, file_size)
        
        # Small file: direct upload
        args = json.dumps({
            'path': dest_path,
            'mode': 'overwrite',
            'autorename': True
        })
        
        with open(local_path, 'rb') as f:
            resp = http_requests.post(
                f'{self.CONTENT_BASE}/files/upload',
                headers={
                    **self._headers(),
                    'Content-Type': 'application/octet-stream',
                    'Dropbox-API-Arg': args
                },
                data=f
            )
            resp.raise_for_status()
        
        result = resp.json()
        logger.info(f"Dropbox upload complete: {filename} -> {result.get('path_display')}")
        return result.get('path_display')
    
    def _upload_large_file(self, local_path, dest_path, file_size):
        chunk_size = 50 * 1024 * 1024  # 50MB chunks
        
        with open(local_path, 'rb') as f:
            # Start session
            chunk = f.read(chunk_size)
            resp = http_requests.post(
                f'{self.CONTENT_BASE}/files/upload_session/start',
                headers={
                    **self._headers(),
                    'Content-Type': 'application/octet-stream',
                    'Dropbox-API-Arg': json.dumps({'close': False})
                },
                data=chunk
            )
            resp.raise_for_status()
            session_id = resp.json()['session_id']
            offset = len(chunk)
            
            # Append chunks
            while offset < file_size:
                chunk = f.read(chunk_size)
                is_last = (offset + len(chunk)) >= file_size
                
                if is_last:
                    # Finish session
                    args = json.dumps({
                        'cursor': {'session_id': session_id, 'offset': offset},
                        'commit': {
                            'path': dest_path,
                            'mode': 'overwrite',
                            'autorename': True
                        }
                    })
                    resp = http_requests.post(
                        f'{self.CONTENT_BASE}/files/upload_session/finish',
                        headers={
                            **self._headers(),
                            'Content-Type': 'application/octet-stream',
                            'Dropbox-API-Arg': args
                        },
                        data=chunk
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    logger.info(f"Dropbox large upload complete: {dest_path}")
                    return result.get('path_display')
                else:
                    args = json.dumps({
                        'cursor': {'session_id': session_id, 'offset': offset}
                    })
                    resp = http_requests.post(
                        f'{self.CONTENT_BASE}/files/upload_session/append_v2',
                        headers={
                            **self._headers(),
                            'Content-Type': 'application/octet-stream',
                            'Dropbox-API-Arg': args
                        },
                        data=chunk
                    )
                    resp.raise_for_status()
                
                offset += len(chunk)
        
        return None


# Factory
PROVIDERS = {
    'google_drive': GoogleDriveManager,
    'onedrive': OneDriveManager,
    'dropbox': DropboxManager
}


def get_cloud_manager(provider, client_id, client_secret, redirect_uri):
    """Factory: create cloud manager for a given provider"""
    cls = PROVIDERS.get(provider)
    if not cls:
        raise ValueError(f"Unknown cloud provider: {provider}")
    return cls(client_id, client_secret, redirect_uri)


def zip_directory(source_dir, output_path=None):
    """Zip an entire directory for cloud upload"""
    if not output_path:
        output_path = f"{source_dir}.zip"
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, source_dir)
                zf.write(file_path, arcname)
    
    return output_path
