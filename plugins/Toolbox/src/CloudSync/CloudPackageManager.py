from cura.CuraApplication import CuraApplication
from plugins.Toolbox.src.CloudApiModel import CloudApiModel
from plugins.Toolbox.src.UltimakerCloudScope import UltimakerCloudScope


## Manages Cloud subscriptions. When a package is added to a user's account, the user is 'subscribed' to that package
# Whenever the user logs in on another instance of Cura, these subscriptions can be used to sync the user's plugins
class CloudPackageManager:

    def __init__(self, app: CuraApplication):
        self._request_manager = app.getHttpRequestManager()
        self._scope = UltimakerCloudScope(app)

    def subscribe(self, package_id: str):
        data = "{\"data\": {\"package_id\": \"%s\", \"sdk_version\": \"%s\"}}" % (package_id, CloudApiModel.sdk_version)
        self._request_manager.put(url=CloudApiModel.api_url_user_packages,
                                  data=data.encode(),
                                  scope=self._scope
                                  )
