import logging
import os
import re
import time

from enchants import Enchants
from wow_api import WoWAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ArmoryAPI')


class ArmoryAPI:

    def __init__(self):
        self.api = WoWAPI(os.environ['BNET_KEY'], os.environ['BNET_SECRET_KEY'])
        logger.info("Armory init")

    def find_char(self, char_name: str, realm: str = None) -> str:
        try_bb = 0

        if not realm:
            logger.info("Realm not set - setting Drak'thul as default")
            realm = "drakthul"
            try_bb = 1
        elif realm == "burningblade" or realm == "Burning Blade":
            realm = "burning-blade"

        try:
            logger.info(f"Searching for {char_name} on {realm}..")
            resp = self.api.get_equipment(char_name, realm)
        except Exception as e:
            if try_bb:
                logger.info("Character wasn't found on Drak'thul - checking Burning Blade")
                return self.find_char(char_name, realm="Burning Blade")
            if "404" in str(e):
                return f"Chyba: Postava {char_name} nenalezena ani na Drak'thul, ani na Burning Blade"
            else:
                return f"Nastala neznámá chyba: {e}"

        logger.info(f"Successfully found {char_name} on {realm}!")
        return resp

    def parse_result(self, equipment):
        gem_state = True
        ench_state = True
        for item in equipment:
            if item['slot']['type'] in ("FINGER_1", "FINGER_2", "MAIN_HAND", "OFF_HAND"):

                if item['slot']['type'] == "OFF_HAND":
                    if item['item_subclass']['name'] in ("Shield", "Miscellaneous"):
                        continue

                ench_json = item.get('enchantments')
                if not ench_json:
                    ench_state = False
                    break

                if item['slot']['type'] in ("FINGER_1", "FINGER_2"):
                    if ench_json[0]['enchantment_id'] not in Enchants.BIG_RING_ENCHANTS.keys():
                        ench_state = False
                        break

                if item['slot']['type'] in ("MAIN_HAND", "OFF_HAND"):
                    if ench_json[0]['enchantment_id'] not in Enchants.WEAPON_ENCHANTS.keys():
                        ench_state = False
                        break

        for item in equipment:
            sock_json = item.get("sockets")
            if sock_json:
                if not sock_json[0].get('item'):
                    gem_state = False
                    break

        return ench_state, gem_state

    def get_guild_members(self):
        logger.info("Getting guild roster..")
        guild = self.api.get_guild_roster("wolves-of-darkness", "drakthul")
        guild_roster = []
        for member in guild:
            if int(member["rank"]) < 3:
                guild_member = {
                    "name": member['character']['name'].lower(),
                    "realm": member['character']['realm']["slug"].lower()
                }
                guild_roster.append(guild_member)
        logger.info(f"Guild roster: {guild_roster}")
        return sorted(guild_roster, key=lambda k: k["name"])

    def check_members(self):
        guild_roster = self.get_guild_members()
        result = "\n|         Postava         |  iLvl  |   Ench   |   Gem   |\n"
        max_len = 15
        for guild_member in guild_roster:
            current_member = self.find_char(char_name=guild_member['name'], realm=guild_member['realm'])
            enchants, gems = self.parse_result(current_member)
            enchanted = ":white_check_mark:" if enchants else ":no_entry:"
            gemmed = ":white_check_mark:" if gems else ":no_entry:"

            spaces = (max_len - len(guild_member['name'])) * "."
            ilvl = self.api.get_summary(guild_member['name'], guild_member['realm'])['equipped_item_level']

            message = f"|`{guild_member['name'].capitalize()}{spaces}`|  `{ilvl}`  |    {enchanted}    |    {gemmed}    |\n"
            result = result + message

        return result

    def print_enchants_and_gems_on_both_realms(self, char_name: str) -> str:
        response = self.print_enchants_and_gems(char_name, realm="drakthul")
        response = response + "\n" + "- - - - "*10 + "\n \n"
        response = response + self.print_enchants_and_gems(char_name, "burning-blade")
        return response

    def print_enchants_and_gems(self, char_name, realm):
        char = self.find_char(char_name, realm)
        enchants, gems = self.parse_result(char)
        response = f"Postava {char_name.capitalize()} - {realm.capitalize()}:\n"
        response += f"Stav enchantů: {':white_check_mark:' if enchants else ':no_entry:'}\n"
        response += f"Stav gemů: {':white_check_mark:' if gems else ':no_entry:'}\n"
        if not gems or not enchants:
            response += "Doplň si to!"
        return response

    def check_corruption(self):
        guild_roster = self.get_guild_members()
        corruption = {}
        for guild_member in guild_roster:
            try:
                logger.info(f"Searching for {guild_member['name']} on {guild_member['realm']}..")
                statistics = self.api.get_statistics(guild_member['name'], guild_member['realm'])
                time.sleep(0.5)
            except Exception as e:
                return e
            corruption[guild_member['name']] = statistics["corruption"]["effective_corruption"]
        return corruption

    def print_corruption(self):
        list_of_corruptions = self.check_corruption()
        result = "\n|         Postava         |  Korupce  |\n"
        for member, corruption in list_of_corruptions.items():
            spaces = (15 - len(member)) * "."
            result += f"|`{member}{spaces}`|       {' ' if corruption < 10 else ''}`{int(corruption)}`{' ' if corruption < 10 else ''}       |\n"
        return result
