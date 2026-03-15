from round import Round
from aioconsole import ainput


class Game:
    def __init__(self):
        self.cur_round = None
        self.rounds_completed = 0

    async def run_game(self):
        still_playing = True
        while still_playing:
            self.cur_round = Round(67)
            await self.cur_round.run_round()
            self.rounds_completed += 1
            post_game_response = await ainput("Play again (y/n)?")
            if post_game_response != "y":
                still_playing = False
