# Created by Jacob Heck on 7-14-2018

#pip3 install --user --upgrade sc2
import random
import numpy as np
import os
import time
import math

import sc2
from sc2 import run_game, maps, Race, Difficulty

from sc2.player import Bot, Computer
from sc2.position import Point2
from sc2.constants import *

class JakeBot(sc2.BotAI):
    def __init__(self):

        self.MAX_WORKERS = 66 # 3 full bases
        self.do_something_after = 2/60
        self.racks = []
        self.racks_add_on = []
        self.racks_no_add_on = []

    async def on_step(self, iteration):

        self.time = (self.state.game_loop/22.4) / 60 #minutes
        self.racks = self.units(BARRACKS).ready

        #print(self.time)
        #print('rack count: {}'.format(len(self.units(BARRACKS))))
        #print('rack ready count: {}'.format(len(self.units(BARRACKS).ready)))
        #print('rack ready noqueue count: {}'.format(len(self.units(BARRACKS).ready.noqueue)))

        if self.racks:
            self.racks_add_on = [x for x in self.racks if x.has_add_on]
            self.racks_no_add_on = [x for x in self.racks if x not in self.racks_add_on]
                #if x.add_on_tag == 0
        await self.distribute_workers()
        await self.build_workers()
        await self.build_supplyDepot()
        await self.build_refinery()
        await self.expand()
        await self.build_offensive_buildings()
        await self.build_offensive_force()
        await self.attack()

##-----------------------------------------------------------------------------

    async def build_workers(self):
        if self.units(SCV).amount < self.units(COMMANDCENTER).amount * 18:
            if self.units(SCV).amount < self.MAX_WORKERS:
                for cc in self.units(COMMANDCENTER).ready.noqueue:
                    if self.can_afford(SCV):
                        await self.do(cc.train(SCV))

    async def build_supplyDepot(self):

        #print('Time:',self.time)
        #print('Cap:',self.supply_cap)
        #print('Left:',self.supply_left)

        build = False
        if not self.already_pending(SUPPLYDEPOT):
            if self.supply_cap < 39:
                if self.supply_left <= 5:
                    build = True
            elif self.supply_cap < 60:
                if self.supply_left <= 10:
                    build = True
            elif self.supply_cap < 200:
                if self.supply_left <= 20:
                    build = True

        if build:
            if len(self.units(COMMANDCENTER).ready) > 0:
                cc = self.units(COMMANDCENTER).ready.random
                if self.can_afford(SUPPLYDEPOT):
                    await self.build(SUPPLYDEPOT, near=cc) #Last CC

            for depo in self.units(SUPPLYDEPOT).ready:
                await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))

    async def build_refinery(self):
        if self.vespene < 300 and self.supply_cap >= 23:
                #or self.already_pending(SUPPLYDEPOT):
                # After one Supply Depot is Built or is being built
            for cc in self.units(COMMANDCENTER).ready:
                vaspenes = self.state.vespene_geyser.closer_than(10.0,cc)
                for vp in vaspenes:
                    worker = self.select_build_worker(vp.position)
                    if self.units(REFINERY).closer_than(1.0,vp).exists:
                        break
                    elif not self.can_afford(REFINERY):
                        break
                    elif worker is None:
                        break
                    else:
                        await self.do(worker.build(REFINERY, vp))

    async def expand(self):
        if self.can_afford(COMMANDCENTER):
            if self.units(COMMANDCENTER).amount <= 2:
                await self.expand_now()
            elif self.units(SCV).idle.amount > 10 and not self.already_pending(COMMANDCENTER):
                await self.expand_now()
            elif self.minerals > 1000 and self.time > 12:
                await self.expand_now()
        '''
        elif self.time > 10 and self.units(COMMANDCENTER).amount < 3:
            while True:
                if self.can_afford(COMMANDCENTER):
                    await self.expand_now()
                    break
        '''

    async def build_offensive_buildings(self):
        if self.can_afford(BARRACKS):
            if self.units(COMMANDCENTER).amount > 1 and self.units(BARRACKS).amount < self.units(COMMANDCENTER).ready.amount * 3:
                cc = self.units(COMMANDCENTER).random
                await self.build(BARRACKS, near=cc.position.towards(self.game_info.map_center, 8), placement_step=5) #8

        '''
        if self.time > 8 and self.can_afford(FACTORY) and self.racks:
            if self.units(COMMANDCENTER).amount > 1 and not self.units(FACTORY).exists:
                cc = self.units(COMMANDCENTER).first
                await self.build(FACTORY, near=cc.position.towards(self.game_info.map_center, 8), placement_step=5) #8

        if self.time > 9 and self.can_afford(STARPORT) and self.units(FACTORY).exists:
            if self.units(COMMANDCENTER).amount > 1 and not self.units(STARPORT).exists:
                cc = self.units(COMMANDCENTER).first
                await self.build(STARPORT, near=cc.position.towards(self.game_info.map_center, 8), placement_step=5) #8
        '''

        if not self.already_pending(BARRACKSTECHLAB):

            rackDiff = 0
            rackCount = len(self.racks)

            if rackCount // 3 > len(self.racks_add_on):
                rackDiff = rackCount // 3 - len(self.racks_add_on)

                if len(self.racks.noqueue) >= rackDiff:
                    for b in self.racks.noqueue.random_group_of(rackDiff):
                        if self.can_afford(BARRACKSTECHLAB):
                            try:
                                await self.do(b.build(BARRACKSTECHLAB))
                            except:
                                print("add on fail: " + str(self.time))
                elif len(self.racks.noqueue) == 0:
                    pass
                else:
                    for b in self.racks.noqueue: #use all since is less than ideal
                        if self.can_afford(BARRACKSTECHLAB):
                            try:
                                await self.do(b.build(BARRACKSTECHLAB))
                            except:
                                print("add on fail: " + str(self.time))

    async def build_offensive_force(self):

        racks = self.racks.noqueue
        racks_add_on = [x for x in racks if x.has_add_on]
        racks_no_add_on = [x for x in racks if x.add_on_tag == 0]

        if racks_add_on:
            for b in racks_add_on:
                if self.can_afford(MARAUDER) and self.supply_left > 1:
                    await self.do(b.train(MARAUDER))

        if racks_no_add_on:
            for b in racks_no_add_on:
                if self.can_afford(MARINE) and self.supply_left > 0:
                    await self.do(b.train(MARINE))

    """
    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]
    """

#attack_towards

    async def attack(self):

        if self.time > self.do_something_after:

            #nearBaseUnits = []
            #nearUnits = []
            #currentAttack = []
            #marineArmy = self.units(MARINE).ready
            ArmyIdle = self.units(MARINE).idle + self.units(MARAUDER).idle
            enemy_units = self.known_enemy_units
            #enemy_buildings = self.known_enemy_structures

            # Find CC Under Attack
            """
            if enemy_units:
                for e in enemy_units:
                    for cc in self.units(COMMANDCENTER):
                        if e.distance_to(cc.position) < 20:
                            nearBaseUnits.append(e)
                            break
            """

            # Find Marines Under Attack, and attack back
            """
            for m in self.units(MARINE):
                for e in self.known_enemy_units:
                    if e.distance_to(m.position) < 6:
                        await self.do(m.attack(e))
                        break
                        #nearUnits.append(e)
            """
            """
            if marineArmy:

                if len(nearBaseUnits) > 3:
                    if len(nearBaseUnits) < len(marineArmy):
                        for m in marineArmy:
                            await self.do(m.attack(random.choice(nearBaseUnits)))
            """
                #elif len(nearUnits) > 0:
                    #for m in marineArmy:
                        #await self.do(m.attack(random.choice(nearUnits)))
                #elif
            if (len(ArmyIdle) > 8 and len(ArmyIdle) > (self.time ** 1.5)) or len(ArmyIdle) > 50:
                if enemy_units:
                    for m in ArmyIdle:
                        await self.do(m.attack(enemy_units.closest_to(self.units(COMMANDCENTER).first)))
                    '''
                    elif enemy_buildings:
                        for m in ArmyIdle:
                            await self.do(m.attack(enemy_buildings.closest_to(self.game_info.map_center)))

                    # Causes Army to suicide into enemy
                    '''
                else:
                    for m in ArmyIdle:
                        await self.do(m.attack(self.enemy_start_locations[0]))

            self.do_something_after = (self.time + 2/60)


##-----------------------------------------------------------------------------

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Terran, JakeBot()),
    Computer(Race.Zerg, Difficulty.Harder)
], realtime=False)

#Difficulties
# very_easy, easy, medium, medium_hard, hard, harder, very_hard
# cheat_vision, cheat_money, cheat_insane
