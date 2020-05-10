import requests


class WoWAPI:

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def _get_url(self, path):
        token = self._get_token()
        url = f"https://eu.api.blizzard.com{path}?namespace=profile-eu&locale=en_GB&access_token={token}"
        print(url)
        response = requests.get(url,
                                headers={'Authorization': f'Bearer {token}'})
        if not response.status_code == 200:
            raise ConnectionError(f"Couldn't get the data!\nFollowing error occurred: {response.status_code}")
        return response.json()

    def _get_token(self) -> str:
        r = requests.get("https://eu.battle.net/oauth/token", auth=(self.client_id, self.client_secret),
                         params={"grant_type": "client_credentials"})
        if not r.status_code == 200:
            raise ConnectionError(f"Couldn't get the access token! \nFollowing error occurred: {r.status_code}")
        token = r.json()
        return token["access_token"]

    def get_equipment(self, name, realm):
        return self._get_url(f"/profile/wow/character/{realm}/{name}/equipment")['equipped_items']

    def get_summary(self, name, realm):
        return self._get_url(f"/profile/wow/character/{realm}/{name}")

    def get_guild_roster(self, name, realm):
        return self._get_url(f"/data/wow/guild/{realm}/{name}/roster")["members"]

    def get_statistics(self, name, realm):
        return self._get_url(f"/profile/wow/character/{realm}/{name}/statistics")
