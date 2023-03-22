# This file is part of Ansible
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from copy import deepcopy

from .clusters import get_cluster_uuid
from .prism import Prism
from .vms import get_vm_uuid


class VolumeGroup(Prism):
    __BASEURL__ = "/api/storage/v4.0.a2/config"

    def __init__(self, module):
        resource_type = "/volume-groups"
        super(VolumeGroup, self).__init__(module, resource_type=resource_type)
        self.build_spec_methods = {
            "name": self._build_spec_name,
            "desc": self._build_spec_desc,
            "cluster": self._build_spec_cluster,
            "target_prefix": self._build_spec_target_prefix,
            "CHAP_auth": self._build_spec_chap_auth,
            "target_password": self._build_spec_target_password,
            "load_balance": self._build_spec_load_balance,
            "flash_mode": self._build_spec_flash_mode,
        }

    def get_vdisks(self, volume_group_uuid, disk_uuid=None):
        if disk_uuid:
            endpoint = "/disks/{0}".format(disk_uuid)
        else:
            endpoint = "/disks"
        return self.read(volume_group_uuid, endpoint=endpoint)

    def get_vms(self, volume_group_uuid):
        endpoint = "/vm-attachments"
        return self.read(volume_group_uuid, endpoint=endpoint)

    def get_clients(self, volume_group_uuid):
        endpoint = "/iscsi-client-attachments"
        return self.read(volume_group_uuid, endpoint=endpoint)

    def create_vdisk(self, spec, volume_group_uuid):
        endpoint = "disks"
        resp = self.update(
            spec, volume_group_uuid, method="POST", endpoint=endpoint, raise_error=False
        )
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp

    def attach_vm(self, spec, volume_group_uuid):
        endpoint = "$actions/attach-vm"

        resp = self.update(
            spec, volume_group_uuid, method="POST", endpoint=endpoint, raise_error=False
        )
        if resp.get("data") and resp["data"].get("error"):
            err = resp["data"]["error"]
            if isinstance(err, list):
                err = err[0]
                if err.get("message"):
                    err = err["message"]
            return None, err

        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp, None

    def attach_iscsi_client(self, spec, volume_group_uuid):
        endpoint = "/$actions/attach-iscsi-client"
        resp = self.update(
            spec, volume_group_uuid, method="POST", endpoint=endpoint, raise_error=False
        )
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp

    def update_disk(self, spec, volume_group_uuid, disk_uuid):
        endpoint = "disks/{0}".format(disk_uuid)
        resp = self.update(
            spec,
            uuid=volume_group_uuid,
            method="PATCH",
            endpoint=endpoint,
            raise_error=False,
        )
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp

    def delete_disk(self, volume_group_uuid, disk_uuid):
        endpoint = "disks/{0}".format(disk_uuid)
        resp = self.delete(uuid=volume_group_uuid, endpoint=endpoint, raise_error=False)
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp

    def detach_vm(self, volume_group_uuid, vm):
        if not vm.get("extId"):
            vm_uuid, err = get_vm_uuid(vm, self.module)
            if err:
                if isinstance(err, list):
                    err = err[0]
                    if err.get("message"):
                        err = err["message"]
                return None, err
        else:
            vm_uuid = vm["extId"]
        endpoint = "$actions/detach-vm/{0}".format(vm_uuid)
        resp = self.update(
            uuid=volume_group_uuid, method="POST", endpoint=endpoint, raise_error=False
        )
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp, None

    def detach_iscsi_client(self, volume_group_uuid, client_uuid):
        endpoint = "$actions/detach-iscsi-client/{0}".format(client_uuid)
        resp = self.update(
            uuid=volume_group_uuid, method="POST", endpoint=endpoint, raise_error=False
        )
        resp["task_uuid"] = resp["data"]["extId"].split(":")[1]
        return resp

    def _get_default_spec(self):
        return deepcopy(
            {
                "name": "",
                "sharingStatus": "SHARED",
                "usageType": "USER",
            }
        )

    def get_update_spec(self):

        return self.get_spec(
            {
                "extId": self.module.params["volume_group_uuid"],
                "sharingStatus": "SHARED",
            }
        )

    def _build_spec_name(self, payload, value):
        payload["name"] = value
        return payload, None

    def _build_spec_desc(self, payload, value):
        payload["description"] = value
        return payload, None

    def _build_spec_target_prefix(self, payload, value):
        payload["iscsiTargetPrefix"] = value
        return payload, None

    def _build_spec_target_password(self, payload, value):
        payload["targetSecret"] = value
        return payload, None

    def _build_spec_chap_auth(self, payload, value):
        if value == "enable":
            payload["enabledAuthentications"] = "CHAP"
        else:
            payload["enabledAuthentications"] = "NONE"
        return payload, None

    def _build_spec_load_balance(self, payload, value):
        payload["loadBalanceVmAttachments"] = value
        return payload, None

    def _build_spec_flash_mode(self, payload, value):

        if value:
            payload["storageFeatures"] = {
                "$objectType": "storage.v4.config.StorageFeatures",
                "$reserved": {
                    "$fqObjectType": "storage.v4.r0.a2.config.StorageFeatures"
                },
                "$unknownFields": {},
                "flashMode": {
                    "$objectType": "storage.v4.config.FlashMode",
                    "$reserved": {"$fqObjectType": "storage.v4.r0.a2.config.FlashMode"},
                    "$unknownFields": {},
                    "isEnabled": True,
                },
            }
        return payload, None

    def _build_spec_cluster(self, payload, param):
        uuid, err = get_cluster_uuid(param, self.module)
        if err:
            return None, err
        payload["clusterReference"] = uuid
        return payload, None

    def get_vm_spec(self, vm):
        uuid, error = get_vm_uuid(vm, self.module)
        if error:
            return None, error
        spec = {"extId": uuid}
        return spec, None

    def get_client_spec(self, client):
        spec = {"extId": client["uuid"]}
        return spec, None


# Helper functions


def get_volume_group_uuid(config, module):
    if "name" in config:
        service_group = VolumeGroup(module)
        name = config["name"]
        uuid = service_group.get_uuid(name)
        if not uuid:
            error = "Volume Group {0} not found.".format(name)
            return None, error
    elif "uuid" in config:
        uuid = config["uuid"]
    else:
        error = "Config {0} doesn't have name or uuid key".format(config)
        return None, error

    return uuid, None
