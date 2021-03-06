from pokemonlib import PokemonGo
import yaml
import asyncio
import re
import argparse

RE_CALCY_IV = re.compile(r"^MainService: Received values: Id: \d+ \((?P<name>.+)\), Nr: (?P<id>\d+), CP: (?P<cp>\d+), Max HP: (?P<max_hp>\d+), Dust cost: (?P<dust_cost>\d+), Level: (?P<level>[0-9\.]+), FastMove (?P<fast_move>.+), SpecialMove (?P<special_move>.+), Gender (?P<gender>\d)$")
RE_RED_BAR = re.compile(r"^av      : Screenshot #\d has red error box at the top of the screen$")
RE_FINISHED = re.compile(r".+\s+: calculateScanOutputData finished after \d+ms$")
RE_SCAN_INVALID = re.compile(r".+\s+: Scan invalid$")


class CalcyIVError(Exception):
    pass


class RedBarError(Exception):
    pass


class Main:
    def __init__(self, args):
        with open(args.config, "r") as f:
            self.config = yaml.load(f)
        self.args = args

    async def tap(self, location):
        await self.p.tap(*self.config['locations'][location])
        if location in self.config['waits']:
            await asyncio.sleep(self.config['waits'][location])

    async def start(self):
        self.p = PokemonGo()
        await self.p.start_logcat()
        num_errors = 0
        while True:
            try:
                values = await self.check_pokemon()
                num_errors = 0
            except RedBarError:
                continue
            except CalcyIVError:
                num_errors += 1
                if num_errors > args.max_retries:
                    self.tap('next')
                    num_errors = 0
                continue

            await self.tap('dismiss_calcy')
            await self.tap('rename')
            await self.p.key(279) # Paste into rename
            await self.tap('keyboard_ok')
            await self.tap('rename_ok')
            await self.tap('next')

    async def check_pokemon(self):
        await self.p.send_intent("tesmath.calcy.ACTION_ANALYZE_SCREEN", "tesmath.calcy/.IntentReceiver")
        red_bar = False
        values = None
        while True:
            line = await self.p.read_logcat()
            line = line.decode('utf-8').strip()
            line = line[33:] # Strip off date and pid

            match = RE_CALCY_IV.match(line)
            if match:
                values = match

            match = RE_RED_BAR.match(line)
            if match:
                red_bar = True

            match = RE_FINISHED.match(line)
            if match:
                return values

            match = RE_SCAN_INVALID.match(line)
            if match:
                if red_bar:
                    raise RedBarError
                else:
                    raise CalcyIVError
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pokemon go renamer')
    parser.add_argument('--device-id', type=str, default=None,
                        help="Optional, if not specified the phone is automatically detected. Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
    parser.add_argument('--max-retries', type=int, default=5,
                        help="Maximum retries, set to 0 for unlimited.")
    parser.add_argument('--config', type=str, default="config.yaml",
                        help="Config file location.")
    args = parser.parse_args()
    asyncio.run(Main(args).start())
