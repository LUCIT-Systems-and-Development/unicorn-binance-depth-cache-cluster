#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ¯\_(ツ)_/¯
#
# File: packages/lucit-ubdcc-shared-modules/lucit_ubdcc_shared_modules/RestEndpointsBase.py
#
# Project website: https://www.lucit.tech/unicorn-binance-depthcache-cluster.html
# Github: https://github.com/LUCIT-Systems-and-Development/unicorn-binance-depthcache-cluster
# Documentation: https://unicorn-binance-depthcache-cluster.docs.lucit.tech
# PyPI: https://pypi.org/project/lucit-ubdcc-mgmt
# LUCIT Online Shop: https://shop.lucit.services/software/unicorn-depthcache-cluster-for-binance
#
# License: LSOSL - LUCIT Synergetic Open Source License
# https://github.com/LUCIT-Systems-and-Development/unicorn-binance-depthcache-cluster/blob/master/LICENSE
#
# Author: LUCIT Systems and Development
#
# Copyright (c) 2024-2024, LUCIT Systems and Development (https://www.lucit.tech)
# All rights reserved.

import json
import time

from fastapi import Request
from fastapi.responses import JSONResponse


class RestEndpointsBase:
    def __init__(self, app=None):
        self.app = app
        self.fastapi = app.get_fastapi_instance()

    def create_cluster_info_response(self) -> dict:
        if self.app.data.get('db') is None:
            response = {}
        else:
            response = {"db": {"depthcaches": self.app.data['db'].get('depthcaches'),
                               "license": self.app.data['db'].get('license'),
                               "nodes": self.app.data['db'].get('nodes'),
                               "pods": self.app.data['db'].get('pods'),
                               "timestamp": self.app.data['db'].get('timestamp')},
                        "version": None}
        if self.app.info['name'] == "lucit-ubdcc-mgmt":
            response['version'] = self.app.get_version()
        return response

    @staticmethod
    def create_debug_ok_response(process_start_time: float = None, used_pods: list = None) -> dict:
        return {"request_time": 0,
                "server_execution_time": time.time() - process_start_time,
                "used_pods": used_pods}

    def create_depthcache_list_response(self) -> dict:
        if self.app.data.get('db') is None:
            response = {}
        else:
            response = {"depthcache_list": self.app.data['db'].get_depthcache_list()}
        return response

    def create_depthcache_info_response(self, exchange: str = None, market: str = None) -> dict:
        if self.app.data.get('db') is None:
            response = {}
        else:
            response = {"depthcache_info": self.app.data['db'].get_depthcache_info(exchange=exchange, market=market)}
        return response

    def get_fastapi_instance(self):
        return self.fastapi

    def get_error_response(self, event: str = None, error_id: str = None, message: str = None, params: dict = None,
                           process_start_time: float = None, used_pods: list = None):
        response = {"event": event, "message": message, "result": "ERROR"}
        if error_id is not None:
            response['error_id'] = error_id
        if params:
            response.update(params)
        if process_start_time is not None:
            response['debug'] = {"request_time": 0,
                                 "server_execution_time": time.time() - process_start_time,
                                 "used_pods": used_pods}
        response_sorted = self.app.sort_dict(input_dict=response)
        return JSONResponse(status_code=200, content=response_sorted)

    def get_ok_response(self, event: str = None, params: dict = None, process_start_time: float = None,
                        used_pods: list = None):
        response = {"event": event, "result": "OK"}
        if params:
            response.update(params)
        if process_start_time is not None:
            response['debug'] = {"request_time": 0,
                                 "server_execution_time": time.time() - process_start_time,
                                 "used_pods": used_pods}
        response_sorted = self.app.sort_dict(input_dict=response)
        return JSONResponse(status_code=200, content=response_sorted)

    def is_ready(self):
        try:
            if self.app.data['is_ready'] is True:
                return True
            else:
                if (self.app.data['start_timestamp'] + self.app.mgmt_is_ready_time) < self.app.get_unix_timestamp():
                    self.app.data['is_ready'] = True
                    return True
                else:
                    return False
        except KeyError:
            self.app.data['is_ready'] = False
            self.app.data['start_timestamp'] = self.app.get_unix_timestamp()
            return False

    def register(self):
        self.app.stdout_msg(f"Registering REST endpoints ...", log="info")

        @self.fastapi.get("/test")
        async def test(request: Request):
            return await self.test(request=request)

        @self.fastapi.get("/ubdcc_mgmt_backup")
        @self.fastapi.post("/ubdcc_mgmt_backup")
        async def ubdcc_mgmt_backup(request: Request):
            return await self.ubdcc_mgmt_backup(request=request)

    async def test(self, request: Request):
        event = "TEST"
        response = {"message": f"Hello World!",
                    "headers": f"{request.headers}",
                    "app": self.app.info,
                    "ubdcc_mgmt_backup": self.app.ubdcc_mgmt_backup}
        if self.app.pod_info is not None:
            pod = {"name": self.app.pod_info.metadata.name,
                   "uid": self.app.pod_info.metadata.uid,
                   "namespace": self.app.pod_info.metadata.namespace,
                   "labels": self.app.pod_info.metadata.labels,
                   "node": self.app.pod_info.spec.node_name}
            response['pod'] = pod
        return self.get_ok_response(event=event, params=response)

    def throw_error_if_mgmt_not_ready(self, request: Request, event: str = None):
        if self.is_ready() is False:
            self.app.stdout_msg(f"Mgmt Service is not ready yet! Telling '{request.query_params.get('uid')}' to come "
                                f"back later!", log="warn")
            return self.get_error_response(event=event, error_id="#1014",
                                           message=f"Mgmt Service is not ready yet! Please come back in a few seconds!")
        else:
            return None

    async def ubdcc_mgmt_backup(self, request: Request):
        event = "UBDCC_MGMT_BACKUP"
        request_body = await request.body()
        if not request_body.decode('utf-8').strip('"'):
            # Get request:
            # provide timestamp of the stored backup
            backup_timestamp = request.query_params.get("get_backup_timestamp")
            if backup_timestamp is not None:
                return self.get_ok_response(event=event, params={"timestamp": self.app.get_backup_timestamp()})
            # provide the backup data for restore
            self.app.stdout_msg(f"Provided backup database!", log="info")
            return self.get_ok_response(event=event, params={"db": self.app.ubdcc_mgmt_backup})
        else:
            # Post request: save the backup data
            if self.app.info['name'] != "lucit-ubdcc-mgmt":
                self.app.data['db-cache'] = json.loads(request_body)
                try:
                    self.app.data['db'].replace_data(data=self.app.data['db-cache'])
                except KeyError as error_msg:
                    self.app.stdout_msg(f"Database not available: {error_msg}", log="debug", stdout=False)
            self.app.ubdcc_mgmt_backup = json.loads(request_body.decode('utf-8'))
            return self.get_ok_response(event=event, params={"message": "The backup has been saved!"})
