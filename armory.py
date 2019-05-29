import logging

import requests
# from wowapi import API
# from wowapi import API.ArmoryAPI
# import wowapi
from wowapi.api import WowApi


# api = WoWApi()
from wowapi.exceptions import WowApiException

from __auth._auth import Auth
from enchants import Enchants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ArmoryAPI')


# noinspection PyDictCreation
class ArmoryAPI:

    def __init__(self):
        self.api = WowApi(Auth.BNET_KEY, Auth.BNET_SECRET_KEY)
        logger.info("Armory init")

    def find_char(self, char_name: str, realm: str = None) -> str:
        try_bb = 0

        if realm == "BurningBlade":
            realm = "Burning Blade"

        if realm is None:
            logger.info("Realm not set - setting Drak'thul as default")
            realm = "Drak'thul"
            try_bb = 1
        try:
            resp = self.api.get_character_profile('eu', realm, char_name, fields='items')
            audit = self.api.get_character_profile('eu', realm, char_name, fields='audit')
        except WowApiException as e:
            if try_bb:
                logger.info("Character wasn't found on Drak'thul - checking Burning Blade")
                return self.find_char(char_name, realm="Burning Blade")
            if "404" in str(e):
                return f"Chyba: Postava {char_name} nenalezena ani na Drak'thul, ani na Burning Blade"
            else:
                return f"Nastala neznámá chyba: {e}"

        enchants, gems = self.parse_result(resp, audit)
        response = f"Postava: {resp['name']} - {resp['realm']} \n"
        response = response + self.check_enchants(enchants) + "\n"
        response = response + self.check_gems(gems) + "\n"
        return response

    def parse_result(self, profile, audit) -> tuple:
        result = {
            "finger1": {
                "name": "",
                "itemLevel": 0,
                "enchant": 0,
                "error": "",
            },
            "finger2": {
                "name": "",
                "itemLevel": 0,
                "enchant": 0,
                "error": "",
            },
            "mainHand": {
                "name": "",
                "itemLevel": 0,
                "enchant": 0,
                "error": "",
            },
            "offHand": {
                "name": "",
                "itemLevel": 0,
                "enchant": 0,
                "error": "",
            },
        }

        simple_item = {
            "name": "",
            "slot": "",
            "itemLevel": "",
        }

        empty_gems = audit['audit']['emptySockets']
        gems = audit['audit']['itemsWithEmptySockets']

        slots = {
            0: "head",
            1: "neck",
            2: "shoulder",
            3: "shirt",
            4: "chest",
            5: "waist",
            6: "legs",
            7: "feet",
            8: "wrist",
            9: "hands",
            10: "finger1",
            11: "finger2",
            12: "trinket1",
            13: "trinket2",
            14: "back",
            15: "mainHand",
            16: "offHand",
        }

        array_of_simple_items = []
        for item, key in profile['items'].items():

            # ------------------------------------------------------------
            # enchant checking
            if empty_gems != 0:
                for gem_item, gem_key in gems.items():
                    if item == slots.get(int(gem_item)):

                        simple_item["name"] = key['name']
                        simple_item["slot"] = item
                        simple_item["itemLevel"] = key['itemLevel']
                        array_of_simple_items.append(simple_item)

            if "finger" in item or "mainHand" in item or "offHand" in item:
                if key['armor'] != 0:
                    continue
                result[item]['name'] = key['name']
                result[item]['itemLevel'] = key['itemLevel']
                try:
                    result[item]['enchant'] = key['tooltipParams']['enchant']
                except KeyError:
                    result[item]['enchant'] = 0

        return result, array_of_simple_items

    def check_enchants(self, enchantable_items: dict) -> str:

        # filter out empty items (eg. only one ring, only one weapon etc)
        to_delete = []
        for item, key in enchantable_items.items():
            if key['name'] == "":
                to_delete.append(item)
        for empty_item in to_delete:
            enchantable_items.pop(empty_item)

        missing = []
        for item, key in enchantable_items.items():
            if "finger" in item:
                if key['enchant'] == 0:
                    key['error'] = "missing"
                    missing.append({item: key})
                try:
                    Enchants.BIG_RING_ENCHANTS.get(key['enchant'])
                except KeyError:
                    try:
                        Enchants.SMALL_RING_ENCHANTS.get(key['enchant'])
                        key['error'] = "small"
                        missing.append({item: key})
                    except KeyError:
                        key['error'] = "unknown"
                        missing.append({item: key})
            if "Hand" in item:
                if key['enchant'] == 0:
                    key['error'] = "missing"
                    missing.append({item: key})
                try:
                    Enchants.WEAPON_ENCHANTS.get(key['enchant'])
                except KeyError:
                    key['error'] = "unknown"
                    missing.append({item: key})
        response = ""

        items = {
            "finger1": "prstenu",
            "finger2": "prstenu",
            "mainHand": "zbrani (mainhand)",
            "offHand": "zbrani (offhand)"
        }

        for item in missing:
            item_name = list(item.keys())[0]
            if item[item_name]['error'] == "missing":
                response = response + f":scream: Chybí enchant na {items.get(item_name)} [{item[item_name]['name']}], ilvl: {item[item_name]['itemLevel']} :scream:\n"

            if item[item_name]['error'] == "small":
                response = response + f":scream: Malý enchant na {items.get(item_name)} [{item[item_name]['name']}] ({Enchants.SMALL_RING_ENCHANTS.get(item[item_name]['enchant'])}), ilvl: {item[item_name]['itemLevel']} :scream: \n"

            if item[item_name]['error'] == "unknown":
                response = response + f":scream: Neznámý enchant na {items.get(item_name)} [{item[item_name]['name']}] (ID: {item[item_name]['enchant']}), ilvl: {item[item_name]['itemLevel']} :scream:\n"

        if response == "":
            response = ":blush: Všechny enchanty jsou v pořádku! :blush:"
        return str(response)

    def check_gems(self, gems):
        response = ""
        if len(gems) == 0:
            response = ":blush: Všechny gemy jsou v pořádku! :blush:"
        else:
            for gem in gems:
                response = response + f":scream: Chybí gem v itemu [{gem['name']}] (slot: {gem['slot']}), ilvl: {gem['itemLevel']} :scream: \n"
        return response

