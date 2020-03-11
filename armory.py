import logging
import os
import re
import time

from wowapi.api import WowApi
from wowapi.exceptions import WowApiException

from enchants import Enchants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ArmoryAPI')


# noinspection PyDictCreation
class ArmoryAPI:

    def __init__(self):
        self.api = WowApi(os.environ['BNET_KEY'], os.environ['BNET_SECRET_KEY'])
        logger.info("Armory init")

    def find_char(self, char_name: str, realm: str = None) -> str:
        try_bb = 0

        if realm is None:
            logger.info("Realm not set - setting Drak'thul as default")
            realm = "Drak'thul"
            try_bb = 1
        elif realm == "burningblade":
            # TODO yeah, i don't know either - maybe list all realms
            realm = "Burning Blade"
        else:
            if not " " in realm:
                logger.info(f"Received realm {realm}, parsing it into two words..")
                realm = " ".join(re.findall('[A-Z][^A-Z]*', realm))
                logger.info(f"Realm parsed as {realm}")

        try:
            logger.info(f"Searching for {char_name} on {realm}..")
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

        logger.info(f"Successfully found {char_name} on {realm}!")
        enchants, gems = self.parse_result(resp, audit)
        response = f"Postava: {resp['name']} - {resp['realm']} \n"
        response = response + f"ItemLevel: {resp['items']['averageItemLevelEquipped']} \n"
        response = response + self.check_enchants(enchants) + "\n"
        response = response + self.check_gems(gems) + "\n"
        if "ilvl" in response:
            response = response + f"Doplň si to, {resp['name']}! \n"
        else:
            response = response + f"Vzorná práce, {resp['name']}! \n"
        return response

    def parse_result(self, profile, audit) -> tuple:

        # Predefined dictionaries that I'm going to be working with:
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

        item_without_gem = {
            "name": "",
            "slot": "",
            "itemLevel": "",
        }

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

        empty_gems = audit['audit']['emptySockets']  # number of gems
        gems = audit['audit']['itemsWithEmptySockets']  # dict of slots with empty gem slots
        logger.info(f"Checking gems: missing: {empty_gems} empty slots: {gems}")

        array_of_items_without_gems = []
        for item, key in profile['items'].items():

            # Checking for gems:
            if empty_gems != 0:
                for gem_item, gem_key in gems.items():
                    if item == slots.get(int(gem_item)):

                        item_without_gem["name"] = key['name']
                        item_without_gem["slot"] = item
                        item_without_gem["itemLevel"] = key['itemLevel']
                        array_of_items_without_gems.append(item_without_gem)

            # Checking for enchants - only rings and weapons
            if "finger" in item or "mainHand" in item or "offHand" in item:
                if "offHand" in item:
                    if key['armor'] != 0:
                        continue
                    try:
                        key['weaponInfo']
                    except KeyError:
                        continue
                result[item]['name'] = key['name']
                result[item]['itemLevel'] = key['itemLevel']
                try:
                    result[item]['enchant'] = key['tooltipParams']['enchant']
                except KeyError:
                    result[item]['enchant'] = 0

        return result, array_of_items_without_gems

    def check_enchants(self, enchantable_items: dict) -> str:

        # filter out empty items (eg. only one ring, only one weapon etc)
        to_delete = []
        for item, key in enchantable_items.items():
            if key['name'] == "":
                to_delete.append(item)
        for empty_item in to_delete:
            enchantable_items.pop(empty_item)

        missing = []
        # checking the enchants and adding a real error state
        for item, key in enchantable_items.items():
            if "finger" in item:
                if key['enchant'] == 0:
                    key['error'] = "missing"
                    missing.append({item: key})
                else:
                    if Enchants.BIG_RING_ENCHANTS.get(key['enchant']) is None:
                        if Enchants.SMALL_RING_ENCHANTS.get(key['enchant']):
                            key['error'] = "small"
                        else:
                            key['error'] = "unknown"
                        missing.append({item: key})

            if "Hand" in item:
                if key['enchant'] == 0:
                    key['error'] = "missing"
                    missing.append({item: key})
                else:
                    if Enchants.WEAPON_ENCHANTS.get(key['enchant']) is None:
                        key['error'] = "unknown"
                        missing.append({item: key})

        response = ""
        # Quick translation to make it more readable
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
                response = response + f":open_mouth: Malý enchant na {items.get(item_name)} [{item[item_name]['name']}] ({Enchants.SMALL_RING_ENCHANTS.get(item[item_name]['enchant'])}), ilvl: {item[item_name]['itemLevel']} :open_mouth: \n"

            if item[item_name]['error'] == "unknown":
                response = response + f":thinking: Neznámý enchant na {items.get(item_name)} [{item[item_name]['name']}] (ID: {item[item_name]['enchant']}), ilvl: {item[item_name]['itemLevel']} :thinking:\n"

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

    def get_guild_members(self):
        logger.info("Getting guild roster..")
        guild = self.api.get_guild_profile("eu", "Drak'thul", "Wolves of Darkness", fields="members")
        guild_roster = []
        for member in guild["members"]:
            if int(member["rank"]) < 2 or int(member["rank"]) == 3:
                guild_member = {
                    "name": member['character']['name'],
                    "realm": member['character']['realm']
                }
                guild_roster.append(guild_member)
        logger.info(f"Guild roster: {guild_roster}")
        return sorted(guild_roster, key=lambda k: k["name"])

    def check_members(self):
        guild_roster = self.get_guild_members()
        result = "\n|         Postava         |  iLvl  |   Ench   |   Gem   |\n"
        enchanted = ""
        gemmed = ""
        max_len = 15
        for guild_member in guild_roster:
            current_member = self.find_char(char_name=guild_member['name'], realm=guild_member['realm'])
            if "enchant na" in current_member:
                enchanted = ":no_entry:"
            elif not "enchant na" in current_member:
                enchanted = ":white_check_mark:"

            if "gem v" in current_member:
                gemmed = ":no_entry:"
            elif not "gem v" in current_member:
                gemmed = ":white_check_mark:"

            spaces = (max_len - len(guild_member['name'])) * "."
            ilvl = current_member.find("ItemLevel") + len("ItemLevel: ")

            message = f"|`{guild_member['name']}{spaces}`|  `{current_member[ilvl: (ilvl  + 3)]}`  |    {enchanted}    |    {gemmed}    |\n"
            result = result + message

        return result

    def find_char_on_both_realms(self, char_name: str) -> str:
        response = self.find_char(char_name, realm="Drak'thul")
        response = response + "\n" + "- - - - "*10 + "\n \n"
        response = response + self.find_char(char_name, "Burning Blade")
        return response

    def check_corruption(self):
        guild_roster = self.get_guild_members()
        corruption = {}
        for guild_member in guild_roster:
            realm = guild_member["realm"].replace("\'", "").replace(" ", "-").lower()
            char_name = guild_member["name"].lower()
            try:
                logger.info(f"Searching for {char_name} on {realm}..")
                statistics = self.api.get_character_stats_summary('eu', "profile-eu", realm, char_name, locale="en_GB")
                time.sleep(0.5)
            except WowApiException as e:

                if "404" in str(e):
                    return f"Chyba: Postava {char_name} nenalezena ani na Drak'thul, ani na Burning Blade"
                else:
                    return f"Nastala neznámá chyba: {e}"
            except Exception as e:
                return e
            corruption[guild_member['name']] = statistics["corruption"]["effective_corruption"]
        return corruption

    def print_corruption(self):
        list_of_corruptions = self.check_corruption()
        result = "\n|         Postava         |  Korupce  |\n"
        for member, corruption in list_of_corruptions.items():
            spaces = (15 - len(member)) * "."
            result += f"|`{member}{spaces}`|    {' ' if corruption < 10 else ''}`{int(corruption)}`{' ' if corruption < 10 else ''}    |\n"
        return result

