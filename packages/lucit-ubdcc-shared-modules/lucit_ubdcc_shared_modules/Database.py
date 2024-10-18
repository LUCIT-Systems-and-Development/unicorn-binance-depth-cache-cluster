#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ¯\_(ツ)_/¯
#
# File: packages/lucit-ubdcc-mgmt/lucit_ubdcc_mgmt/Database.py
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

import threading
import time


class Database:
    def __init__(self, app=None):
        self.app = app
        self.app.data['db'] = self
        self.data = {}
        self.data_lock = threading.Lock()
        self._init()

    def _init(self) -> bool:
        self.app.stdout_msg(f"Initiating Database ...", log="info")
        self.set(key="depthcaches", value={})
        self.set(key="license", value={"api_secret": "",
                                       "license_token": "",
                                       "status": "INVALID"})
        self.set(key="nodes", value={})
        self.set(key="pods", value={})
        self.set(key="timestamp", value=float())
        if self.app.info['name'] == "lucit-ubdcc-mgmt":
            self.update_nodes()
        return True

    def _set_update_timestamp(self) -> bool:
        self.data['timestamp'] = self.app.get_unix_timestamp()
        return True

    def is_empty(self) -> bool:
        if len(self.data['pods']) == 0 and \
                len(self.data['depthcaches']) == 0 and \
                len(self.data['license']['api_secret']) == 0 and \
                len(self.data['license']['license_token']) == 0:
            return True
        return False

    def add_depthcache(self,
                       exchange: str = None,
                       market: str = None,
                       desired_quantity: int = None,
                       update_interval: int = None,
                       refresh_interval: int = None) -> bool:
        if exchange is None or market is None:
            raise ValueError("Missing mandatory parameter: exchange, market")
        if desired_quantity is None or desired_quantity == "None":
            desired_quantity = 1
        else:
            desired_quantity = int(desired_quantity)
        if update_interval is None or update_interval == "None":
            update_interval = 1000
        else:
            update_interval = int(update_interval)
        if refresh_interval is None or refresh_interval == "None":
            refresh_interval = None
        else:
            refresh_interval = int(refresh_interval)
        depthcache = {"CREATED_TIME": self.app.get_unix_timestamp(),
                      "DESIRED_QUANTITY": desired_quantity,
                      "DISTRIBUTION": {},
                      "EXCHANGE": exchange,
                      "REFRESH_INTERVAL": refresh_interval,
                      "MARKET": market,
                      "UPDATE_INTERVAL": update_interval}
        with self.data_lock:
            if self.data['depthcaches'].get(exchange) is None:
                self.data['depthcaches'][exchange] = {}
            self.data['depthcaches'][exchange][market] = depthcache
            self._set_update_timestamp()
        return True

    def add_depthcache_distribution(self,
                                    exchange: str = None,
                                    market: str = None,
                                    pod_uid: str = None) -> bool:
        if exchange is None or market is None or pod_uid is None:
            raise ValueError("Missing mandatory parameter: exchange, pod_uid, market")
        distribution = {"CREATED_TIME": self.app.get_unix_timestamp(),
                        "LAST_RESTART_TIME": 0,
                        "POD_UID": pod_uid,
                        "STATUS": "starting"}
        with self.data_lock:
            self.data['depthcaches'][exchange][market]['DISTRIBUTION'][pod_uid] = distribution
            self._set_update_timestamp()
        return True

    def add_pod(self, name: str = None, uid: str = None, node: str = None, role: str = None, ip: str = None,
                api_port_rest: int = None, status: str = None, ubldc_version: str = None, version: str = None) -> bool:
        if uid is None:
            raise ValueError("Missing mandatory parameter: uid")
        pod = {"NAME": name,
               "UID": uid,
               "NODE": node,
               "ROLE": role,
               "IP": ip,
               "API_PORT_REST": api_port_rest,
               "LAST_SEEN": self.app.get_unix_timestamp(),
               "STATUS": status,
               "UBLDC_VERSION": ubldc_version,
               "VERSION": version}
        if ubldc_version is None:
            del pod['UBLDC_VERSION']
        with self.data_lock:
            self.data['pods'][uid] = pod
            self._set_update_timestamp()
        return True

    def delete(self, key: str = None) -> bool:
        with self.data_lock:
            if key in self.data:
                del self.data[key]
                self._set_update_timestamp()
                self.app.stdout_msg(f"DB entry deleted: {key}", log="debug", stdout=False)
                return True
        self.app.stdout_msg(f"DB entry {key} not found.", log="debug", stdout=False)
        return False

    def delete_depthcache(self, exchange: str = None, market: str = None) -> bool:
        if exchange is None or market is None:
            raise ValueError("Missing mandatory parameter: exchange, market")
        with self.data_lock:
            try:
                del self.data["depthcaches"][exchange][market]
            except KeyError:
                return True
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB depthcaches deleted: {exchange}, {market}", log="debug")
        return True

    def delete_depthcache_distribution(self, exchange: str = None, market: str = None, pod_uid: str = None) -> bool:
        if exchange is None or market is None or pod_uid is None:
            raise ValueError("Missing mandatory parameter: exchange, pod_uid, market")
        with self.data_lock:
            del self.data["depthcaches"][exchange][market]['DISTRIBUTION'][pod_uid]
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB depthcache distribution deleted: {exchange}, {market}, {pod_uid}", log="debug")
        return True

    def delete_pod(self, uid: str = None) -> bool:
        if uid is None:
            raise ValueError("Missing mandatory parameter: uid")
        with self.data_lock:
            del self.data["pods"][uid]
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB pod deleted: {uid}", log="debug", stdout=True)
        return True

    def delete_old_pods(self) -> bool:
        old_pods = []
        max_age = 60
        with self.data_lock:
            for uid in self.data['pods']:
                if (time.time() - max_age) > self.data['pods'][uid]['LAST_SEEN']:
                    old_pods.append(uid)
        for uid in old_pods:
            self.delete_pod(uid=uid)
        return True

    def exists_depthcache(self, exchange: str = None, market: str = None) -> bool:
        if exchange is None or market is None:
            raise ValueError("Missing mandatory parameter: exchange, market")
        with self.data_lock:
            try:
                return market in self.data['depthcaches'][exchange]
            except KeyError:
                return False

    def exists_pod(self, uid: str = None) -> bool:
        if uid is None:
            raise ValueError("Missing mandatory parameter: uid")
        return uid in self.data['pods']

    def get(self, key: str = None):
        with self.data_lock:
            return self.data.get(key)

    def get_all(self) -> dict:
        with self.data_lock:
            return self.data

    def get_available_dcn_pods(self) -> dict:
        available_dcn_pods = {}
        for uid in self.data['pods']:
            if self.data['pods'][uid]['ROLE'] == "lucit-ubdcc-dcn":
                try:
                    available_dcn_pods[uid] = self.data['nodes'][self.data['pods'][uid]['NODE']]['USAGE_CPU_PERCENT']
                except KeyError:
                    available_dcn_pods[uid] = 0
        return available_dcn_pods

    def get_backup_dict(self) -> dict:
        with self.data_lock:
            return self.app.sort_dict(input_dict=self.app.data['db'].data)

    def get_best_dcn(self, available_pods: dict = None, excluded_pods: list = None):
        if available_pods is None:
            available_pods = self.get_available_dcn_pods()
        delta_pods = {uid: cpu for uid, cpu in available_pods.items() if uid not in excluded_pods}
        if not delta_pods:
            return None
        try:
            best_pod = min(delta_pods, key=lambda uid: delta_pods[uid])
        except TypeError:
            self.app.stdout_msg(f"ERROR: Can not get 'best_pod' from delta_pods: {delta_pods}")
            return None
        return best_pod

    def get_dcn_responsibilities(self) -> list:
        with self.data_lock:
            responsibilities = []
            for exchange in self.data['depthcaches']:
                for market in self.data['depthcaches'][exchange]:
                    for pod_uid in self.data['depthcaches'][exchange][market]['DISTRIBUTION']:
                        if pod_uid == self.app.id['uid']:
                            responsibilities.append({"exchange": exchange,
                                                     "market": market,
                                                     "refresh_interval": self.data['depthcaches'][exchange][market]['REFRESH_INTERVAL'],
                                                     "update_interval": self.data['depthcaches'][exchange][market]['UPDATE_INTERVAL']})
        return responsibilities

    def get_depthcache_list(self) -> dict:
        with self.data_lock:
            try:
                return self.data['depthcaches']
            except KeyError:
                return {}

    def get_depthcache_info(self, exchange: str = None, market: str = None) -> dict:
        if exchange is None or market is None:
            raise ValueError("Missing mandatory parameter: exchange, market")
        with self.data_lock:
            try:
                return self.data['depthcaches'][exchange][market]
            except KeyError:
                return {}

    def get_license_api_secret(self) -> str:
        with self.data_lock:
            return self.data['license']['api_secret']

    def get_license_license_token(self) -> str:
        with self.data_lock:
            return self.data['license']['license_token']

    def get_license_status(self) -> str:
        with self.data_lock:
            return self.data['license']['status']

    def get_pod_by_address(self, address: str = None) -> dict | None:
        if address is None:
            raise ValueError("Missing mandatory parameter: address")
        with self.data_lock:
            try:
                for uid in self.data['pods']:
                    if self.data['pods'][uid]['IP'] == address:
                        return self.data['pods'][uid]
            except KeyError:
                return None

    def get_pod_by_uid(self, uid=None) -> dict | None:
        if uid is None:
            raise ValueError("Missing mandatory parameter: uid")
        with self.data_lock:
            try:
                return self.data['pods'][uid]
            except KeyError:
                return None

    def get_responsible_dcn_addresses(self, exchange: str = None, market: str = None) -> list:
        with self.data_lock:
            responsible_dcn = []
            try:
                for pod_uid in self.data['depthcaches'][exchange][market]['DISTRIBUTION']:
                    if self.data['depthcaches'][exchange][market]['DISTRIBUTION'][pod_uid]['STATUS'] == "running":
                        responsible_dcn.append([self.data['pods'][pod_uid]['IP'],
                                                self.data['pods'][pod_uid]['API_PORT_REST']])
            except KeyError:
                pass
        return responsible_dcn

    def get_worst_dcn(self, available_pods: dict = None, excluded_pods: list = None):
        if available_pods is None:
            available_pods = self.get_available_dcn_pods()
        delta_pods = {uid: cpu for uid, cpu in available_pods.items() if uid not in excluded_pods}
        if not delta_pods:
            return None
        try:
            worst_pod = max(delta_pods, key=lambda uid: delta_pods[uid])
        except TypeError:
            self.app.stdout_msg(f"ERROR: Can not get 'worst_pod' from delta_pods: {delta_pods}")
            return None
        return worst_pod

    def replace_data(self, data: dict = None):
        with self.data_lock:
            self.data = data
        return True

    def remove_orphaned_distribution_entries(self) -> bool:
        with self.data_lock:
            remove_distributions = []
            for exchange in self.data['depthcaches']:
                for market in self.data['depthcaches'][exchange]:
                    for pod_uid in self.data['depthcaches'][exchange][market]['DISTRIBUTION']:
                        if self.exists_pod(uid=pod_uid) is False:
                            remove_distributions.append({"exchange": exchange,
                                                         "market": market,
                                                         "pod_uid": pod_uid})
        with self.data_lock:
            for item in remove_distributions:
                del self.data['depthcaches'][item['exchange']][item['market']]['DISTRIBUTION'][item['pod_uid']]
                self._set_update_timestamp()
        return True

    def revise(self) -> bool:
        start_time = time.time()
        self.app.stdout_msg(f"Revise the Database ...", log="info")
        self.update_nodes()
        self.delete_old_pods()
        self.remove_orphaned_distribution_entries()
        self.manage_distribution()
        run_time = time.time() - start_time
        self.app.stdout_msg(f"Database revised in {run_time} seconds!", log="info")
        return True

    def manage_distribution(self) -> bool:
        add_distributions = []
        remove_distributions = []
        with self.data_lock:
            for exchange in self.data['depthcaches']:
                for market in self.data['depthcaches'][exchange]:
                    existing_distribution = {}
                    for pod_uid in self.data['depthcaches'][exchange][market]['DISTRIBUTION']:
                        try:
                            existing_distribution[pod_uid] = self.data['nodes'][self.data['pods'][pod_uid]['NODE']]['USAGE_CPU_PERCENT']
                        except KeyError:
                            existing_distribution[pod_uid] = 0
                    existing_quantity = len(self.data['depthcaches'][exchange][market]['DISTRIBUTION'])
                    desired_quantity = self.data['depthcaches'][exchange][market]['DESIRED_QUANTITY']
                    if existing_quantity < desired_quantity:
                        add_quantity = desired_quantity - existing_quantity
                        exclude_dcn = list(existing_distribution.keys())
                        for _ in range(0, add_quantity):
                            best_dcn = self.get_best_dcn(excluded_pods=exclude_dcn)
                            if best_dcn is not None:
                                exclude_dcn.append(best_dcn)
                                add_distributions.append({"exchange": exchange,
                                                          "market": market,
                                                          "pod_uid": best_dcn})
                    elif existing_quantity > desired_quantity:
                        remove_quantity = existing_quantity - desired_quantity
                        exclude_dcn = []
                        for _ in range(0, remove_quantity):
                            worst_dcn = self.get_worst_dcn(available_pods=existing_distribution,
                                                           excluded_pods=exclude_dcn)
                            if worst_dcn is not None:
                                exclude_dcn.append(worst_dcn)
                                remove_distributions.append({"exchange": exchange,
                                                             "market": market,
                                                             "pod_uid": worst_dcn})
        for item in add_distributions:
            self.add_depthcache_distribution(exchange=item['exchange'],
                                             market=item['market'],
                                             pod_uid=item['pod_uid'])
        for item in remove_distributions:
            self.delete_depthcache_distribution(exchange=item['exchange'],
                                                market=item['market'],
                                                pod_uid=item['pod_uid'])
        return True

    def set(self, key: str = None, value: dict | str | float | list | set | tuple = None) -> bool:
        with self.data_lock:
            self.data[key] = value
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB entry added/updated: {key} = {value}", log="debug", stdout=False)
        return True

    def set_license_status(self, status: str = None) -> bool:
        if status is None:
            raise ValueError("Missing mandatory parameter: status")
        with self.data_lock:
            self.data['license']['status'] = status
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB license status change to: {status}", log="debug", stdout=False)
        return True

    def submit_license(self, api_secret: str = None, license_token: str = None) -> bool:
        if api_secret is None or license_token is None:
            raise ValueError("Missing mandatory parameter: api_secret, license_token")
        with self.data_lock:
            self.data['license']['api_secret'] = api_secret
            self.data['license']['license_token'] = license_token
            self._set_update_timestamp()
        self.app.stdout_msg(f"DB license submitted: {api_secret}, {license_token}", log="debug", stdout=False)
        return True

    def update_nodes(self) -> bool:
        nodes = self.app.get_k8s_nodes()
        if nodes:
            self.set(key="nodes", value=nodes)
            self.app.stdout_msg(f"DB all nodes updated!", log="debug", stdout=False)
            return True
        else:
            self.app.stdout_msg(f"Timed update of the DB key 'nodes': Query of the k8s nodes was empty, no "
                                f"update is performed!", log="error", stdout=True)
            return False

    def update_depthcache(self,
                          desired_quantity: int = None,
                          exchange: str = None,
                          refresh_interval: int = None,
                          market: str = None,
                          update_interval: int = None) -> bool:
        if exchange is None or market is None:
            raise ValueError("Missing mandatory parameter: exchange, market")
        with self.data_lock:
            if desired_quantity is not None:
                self.data['depthcaches'][exchange][market]['DESIRED_QUANTITY'] = desired_quantity
                self._set_update_timestamp()
            if update_interval is not None:
                self.data['depthcaches'][exchange][market]['UPDATE_INTERVAL'] = update_interval
                self._set_update_timestamp()
            if refresh_interval is not None:
                self.data['depthcaches'][exchange][market]['REFRESH_INTERVAL'] = refresh_interval
                self._set_update_timestamp()
        self.app.stdout_msg(f"DB depthcaches updated: {exchange}, {market}, {desired_quantity}, {update_interval}",
                            log="debug")
        return True

    def update_depthcache_distribution(self,
                                       exchange: str = None,
                                       market: str = None,
                                       pod_uid: str = None,
                                       last_restart_time: float = None,
                                       status: str = None) -> bool:
        if exchange is None or market is None or pod_uid is None:
            raise ValueError("Missing mandatory parameter: exchange, pod_uid, market")
        with self.data_lock:
            if last_restart_time is not None:
                self.data['depthcaches'][exchange][market]['DISTRIBUTION'][pod_uid]['LAST_RESTART_TIME'] = \
                    last_restart_time
                self._set_update_timestamp()
            if status is not None:
                try:
                    self.data['depthcaches'][exchange][market]['DISTRIBUTION'][pod_uid]['STATUS'] = status
                except KeyError:
                    return False
                self._set_update_timestamp()
        self.app.stdout_msg(f"DB depthcache distribution updated: {exchange}, {market}, {pod_uid}, {last_restart_time},"
                            f"{status}", log="debug")
        return True

    def update_pod(self, uid: str = None, node: str = None, ip: str = None, api_port_rest: int = None,
                   status: str = None) -> bool:
        if uid is None:
            raise ValueError("Missing mandatory parameter: uid")
        with self.data_lock:
            self.data['pods'][uid]['LAST_SEEN'] = self.app.get_unix_timestamp()
            if api_port_rest is not None:
                self.data['pods'][uid]['API_PORT_REST'] = api_port_rest
                self._set_update_timestamp()
            if ip is not None:
                self.data['pods'][uid]['IP'] = ip
                self._set_update_timestamp()
            if node is not None:
                self.data['pods'][uid]['NODE'] = node
                self._set_update_timestamp()
            if status is not None:
                self.data['pods'][uid]['STATUS'] = status
                self._set_update_timestamp()
        self.app.stdout_msg(f"DB pod updated: {uid}", log="debug", stdout=False)
        return True
