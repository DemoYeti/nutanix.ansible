#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2021, Prem Karat
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
from copy import deepcopy

__metaclass__ = type


from ..module_utils.ndb.base_module import NdbBaseModule  # noqa: E402
from ..module_utils.utils import remove_param_with_none_value  # noqa: E402
from ..module_utils.ndb.time_machines import TimeMachine


def get_module_spec():
    mutually_exclusive = [("name", "uuid")]
    entity_by_spec = dict(name=dict(type="str"), uuid=dict(type="str"))

    module_args = dict(
        db_server_vms=dict(
            type="list",
            elements="dict",
            options=entity_by_spec,
            mutually_exclusive=mutually_exclusive,
            required=True,
        ),
        time_machine=dict(
            type="dict",
            options=entity_by_spec,
            mutually_exclusive=mutually_exclusive,
            required=True,
        ),
    )
    return module_args


def authorize_db_server_vms(module, result):
    time_machine = TimeMachine(module)
    if not module.params.get("time_machine"):
        module.fail_json(
            msg="'time_machine' is required for authorizing db server vms with time machine"
        )

    time_machine_uuid, err = time_machine.get_time_machine_uuid(
        module.params.get("time_machine")
    )
    if err:
        result["response"] = err
        module.fail_json(msg="Failed fetching time machine uuid", **result)

    spec, err = time_machine.get_authorize_db_server_vms_spec()
    if err:
        result["response"] = err
        module.fail_json(msg="Failed getting authorizing db server vm spec", **result)

    if module.check_mode:
        result["response"] = spec
        return

    resp = time_machine.authorize_db_server_vms(uuid=time_machine_uuid, data=spec)
    result["response"] = resp
    result["uuid"] = time_machine_uuid
    result["changed"] = True


def run_module():
    module = NdbBaseModule(
        argument_spec=get_module_spec(),
        supports_check_mode=True,
    )
    remove_param_with_none_value(module.params)
    result = {"changed": False, "error": None, "response": None, "uuid": None}
    authorize_db_server_vms(module, result)
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()