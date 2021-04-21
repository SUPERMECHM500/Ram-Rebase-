# IMPORTS
from os import getcwd
from sys import exc_info
from typing import List

from discord import Embed
from dbl.client import DBLClient
from dbl.errors import DBLException
from discord.ext.commands.bot import Bot as DiscordBot

from utils.errorlog import ErrorLog


class Paginator:

    def __init__(
            self,
            page_limit: int = 1000,
            trunc_limit: int = 2000,
            headers: List[str] = None,
            header_extender: str = u'\u200b'
    ):
        self.page_limit = page_limit
        self.trunc_limit = trunc_limit
        self._pages = None
        self._headers = None
        self._header_extender = header_extender
        self.set_headers(headers)

    @property
    def pages(self):
        if self._headers:
            self._extend_headers(len(self._pages))
            headers, self._headers = self._headers, None
            return [
                (headers[i], self._pages[i]) for i in range(len(self._pages))
            ]
        else:
            return self._pages

    def set_headers(self, headers: List[str] = None):
        self._headers = headers

    def set_header_extender(self, header_extender: str = u'\u200b'):
        self._header_extender = header_extender

    def _extend_headers(self, length: int):
        while len(self._headers) < length:
            self._headers.append(self._header_extender)

    def set_trunc_limit(self, limit: int = 2000):
        self.trunc_limit = limit

    def set_page_limit(self, limit: int = 1000):
        self.page_limit = limit

    def paginate(self, value):
        """
        To paginate a string into a list of strings under
        `self.page_limit` characters. Total len of strings
        will not exceed `self.trunc_limit`.
        :param value: string to paginate
        :return list: list of strings under 'page_limit' chars
        """
        spl = str(value).split('\n')
        ret = []
        page = ''
        total = 0
        for i in spl:
            if total + len(page) < self.trunc_limit:
                if (len(page) + len(i)) < self.page_limit:
                    page += '\n{}'.format(i)
                else:
                    if page:
                        total += len(page)
                        ret.append(page)
                    if len(i) > (self.page_limit - 1):
                        tmp = i
                        while len(tmp) > (self.page_limit - 1):
                            if total + len(tmp) < self.trunc_limit:
                                total += len(tmp[:self.page_limit])
                                ret.append(tmp[:self.page_limit])
                                tmp = tmp[self.page_limit:]
                            else:
                                ret.append(tmp[:self.trunc_limit - total])
                                break
                        else:
                            page = tmp
                    else:
                        page = i
            else:
                ret.append(page[:self.trunc_limit - total])
                break
        else:
            ret.append(page)
        self._pages = ret
        return self.pages


class Bot(DiscordBot):

    def __init__(self, *args, **kwargs):

        # Namespace variables, not saved to files
        self.inactive = 0  # Timer to track minutes since responded to a command
        self.waiting: List[int] = list()  # Users waiting for a response from developer
        self.cwd = getcwd()  # Global bot directory
        self.text_status = f"{kwargs.get('command_prefix')}help"  # Change first half of text status

        # Namespace variable to indicate if a support thread is open or not.
        # If true, the developer cannot accept a support message if another is already active.
        self.thread_active = False

        # Alias for user_data['config']
        self.config = kwargs.pop("config") 

         # Online database
        self.database = kwargs.pop("database")

        # Local copy of the database
        self.user_data = kwargs.pop("user_data")
        print("[BOT INIT] Loaded data.")

        # To be filled by self.connect_dbl() in on_ready
        self.dbl: DBLClient = kwargs.pop("dbl", None)

        # Attribute for accessing tokens from database
        self.auth = kwargs.pop("auth")

        # Get the channel ready for errorlog
        # Bot.get_channel method not available until on_ready
        self.errorlog_channel: int = kwargs.pop("errorlog", None)
        self.errorlog: ErrorLog = kwargs.get("errorlog", None)

        # Load bot arguments into __init__
        super().__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        print("[BOT INIT] Logging in with token.")
        super().run(self.auth["BOT_TOKEN"], *args, **kwargs)
    
    @property
    def dbl_page(self):
        return f"https://discordbots.org/bot/{self.user.id}"

    @property
    def dbl_vote(self):
        return f"{self.dbl_page}/vote"

    async def connect_dbl(self, autopost: bool = None):
        try:
            if self.dbl:
                await self.dbl.close()
            token = self.auth.get("DBL_TOKEN")

            self.dbl = DBLClient(self, token, autopost=autopost)
            await self.dbl.post_guild_count()

            print("[DBL LOGIN] Logged in to DBL with token.")

        except DBLException:
            await self.dbl.close()
            self.auth["MWS_DBL_TOKEN"] = None
            self.dbl = None

            print("[DBL ERROR] Login Failed: No token was provided or token provided was invalid.")

    async def get_user_vote(self, user_id: int):
        if user_id in self.owner_ids:
            return True

        elif not self.dbl:
            return None

        return await self.dbl.get_user_vote(user_id)
    
    async def on_error(self, event_name, *args, **kwargs):
        '''Error handler for Exceptions raised in events'''
        if self.config["debug_mode"]:  # Hold true the purpose for the debug_mode option
            await super().on_error(event_method=event_name, *args, **kwargs)
            return
        
        # Try to get Exception that was raised
        error = exc_info()  # `from sys import exc_info` at the top of your script

        # If the Exception raised is successfully captured, use ErrorLog
        if error:
            await self.errorlog.send(error, event=event_name)

        # Otherwise, use default handler
        else:
            await super().on_error(event_method=event_name, *args, **kwargs)


# Override default color for bot fanciness
class ModdedEmbed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = 0xff87a3
        self.colour = self.color