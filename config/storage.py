from cloudinary_storage.storage import MediaCloudinaryStorage
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from django.conf import settings


class OptimizedMediaCloudinaryStorage(MediaCloudinaryStorage):
    """画像URLに f_auto,q_auto を自動付与して帯域を節約（旧Cloudinary用、当面残す）"""
    def url(self, name):
        url = super().url(name)
        if url and '/upload/' in url and '/f_auto' not in url:
            url = url.replace('/upload/', '/upload/f_auto,q_auto/', 1)
        return url


# --- ImageKit ヘルパー ---

def get_imagekit_client():
    """ImageKit SDKクライアントを生成して返す"""
    return ImageKit(
        public_key=settings.IMAGEKIT_PUBLIC_KEY,
        private_key=settings.IMAGEKIT_PRIVATE_KEY,
        url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
    )


def upload_to_imagekit(file, file_name, folder='products'):
    """
    ファイルをImageKitにアップロードして、URLとfile_idを返す
    """
    try:
        imagekit = get_imagekit_client()
        
        options = UploadFileRequestOptions(
            folder=f'/{folder}/',
            use_unique_file_name=True,
        )
        
        if hasattr(file, 'seek'):
            file.seek(0)
        
        result = imagekit.upload_file(
            file=file,
            file_name=file_name,
            options=options,
        )
        
        return {
            'url': result.url,
            'file_id': result.file_id,
        }
    except Exception as e:
        print(f'ImageKit upload error: {e}')
        return None


def delete_from_imagekit(file_id):
    """ImageKitからファイルを削除"""
    if not file_id:
        return False
    try:
        imagekit = get_imagekit_client()
        imagekit.delete_file(file_id=file_id)
        return True
    except Exception as e:
        print(f'ImageKit delete error: {e}')
        return False


def bulk_delete_from_imagekit(file_ids):
    """ImageKitから複数ファイルを一括削除（最大100件/回）"""
    if not file_ids:
        return False
    try:
        imagekit = get_imagekit_client()
        for i in range(0, len(file_ids), 100):
            chunk = file_ids[i:i+100]
            imagekit.bulk_delete_files(file_ids=chunk)
        return True
    except Exception as e:
        print(f'ImageKit bulk delete error: {e}')
        return False


def get_optimized_url(url, transformation='f-auto,q-auto'):
    """ImageKit URLに変換パラメータを付与して最適化URLを返す"""
    if not url:
        return url
    if '?tr=' in url:
        return url
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}tr={transformation}'
