from cloudinary_storage.storage import MediaCloudinaryStorage


class OptimizedMediaCloudinaryStorage(MediaCloudinaryStorage):
    """画像URLに f_auto,q_auto を自動付与して帯域を節約"""
    def url(self, name):
        url = super().url(name)
        if url and '/upload/' in url and '/f_auto' not in url:
            url = url.replace('/upload/', '/upload/f_auto,q_auto/', 1)
        return url
