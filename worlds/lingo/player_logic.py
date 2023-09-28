from typing import Dict, List, Optional, NamedTuple
from worlds.AutoWorld import World
from .testing import LingoTestOptions
from .locations import StaticLingoLocations, LocationClassification
from .static_logic import RoomAndPanel, StaticLingoLogic, Door
from .items import StaticLingoItems


class PlayerLocation(NamedTuple):
    name: str
    code: Optional[int] = None
    panels: List[RoomAndPanel] = []


class LingoPlayerLogic:
    """
    Defines logic after a player's options have been applied
    """

    ITEM_BY_DOOR: Dict[str, Dict[str, str]]

    LOCATIONS_BY_ROOM: Dict[str, List[PlayerLocation]]
    REAL_LOCATIONS: List[str]

    EVENT_LOC_TO_ITEM: Dict[str, str]
    REAL_ITEMS: List[str]

    VICTORY_CONDITION: str
    MASTERY_LOCATION: str
    LEVEL_2_LOCATION: str

    PAINTING_MAPPING: Dict[str, str]

    FORCED_GOOD_ITEM: str

    def add_location(self, room: str, loc: PlayerLocation):
        self.LOCATIONS_BY_ROOM.setdefault(room, []).append(loc)

    def set_door_item(self, room: str, door: str, item: str):
        self.ITEM_BY_DOOR.setdefault(room, {})[door] = item

    def handle_non_grouped_door(self, room_name: str, door_data: Door, world: World, static_logic: StaticLingoLogic):
        if room_name in static_logic.PROGRESSION_BY_ROOM \
                and door_data.name in static_logic.PROGRESSION_BY_ROOM[room_name]:
            if room_name == "Orange Tower" and not getattr(world.multiworld, "progressive_orange_tower")[world.player]:
                self.set_door_item(room_name, door_data.name, door_data.item_name)
            else:
                progressive_item_name = static_logic.PROGRESSION_BY_ROOM[room_name][door_data.name].item_name
                self.set_door_item(room_name, door_data.name, progressive_item_name)
                self.REAL_ITEMS.append(progressive_item_name)
        else:
            self.set_door_item(room_name, door_data.name, door_data.item_name)

    def __init__(self, world: World, static_logic: StaticLingoLogic, static_items: StaticLingoItems,
                 static_locat: StaticLingoLocations, test_options: LingoTestOptions):
        self.ITEM_BY_DOOR = {}
        self.LOCATIONS_BY_ROOM = {}
        self.REAL_LOCATIONS = []
        self.EVENT_LOC_TO_ITEM = {}
        self.REAL_ITEMS = []
        self.VICTORY_CONDITION = ""
        self.MASTERY_LOCATION = ""
        self.LEVEL_2_LOCATION = ""
        self.PAINTING_MAPPING = {}
        self.FORCED_GOOD_ITEM = ""

        door_shuffle = getattr(world.multiworld, "shuffle_doors")[world.player]
        color_shuffle = getattr(world.multiworld, "shuffle_colors")[world.player]
        painting_shuffle = getattr(world.multiworld, "shuffle_paintings")[world.player]
        victory_condition = getattr(world.multiworld, "victory_condition")[world.player]

        # Create an event for every room that represents being able to reach that room.
        for room_name in static_logic.ROOMS.keys():
            roomloc_name = f"{room_name} (Reached)"
            self.add_location(room_name, PlayerLocation(roomloc_name, None, []))
            self.EVENT_LOC_TO_ITEM[roomloc_name] = roomloc_name

        # Create an event for every door, representing whether that door has been opened. Also create event items for
        # doors that are event-only.
        for room_name, room_data in static_logic.DOORS_BY_ROOM.items():
            for door_name, door_data in room_data.items():
                if door_shuffle == 0:  # no door shuffle
                    itemloc_name = f"{room_name} - {door_name} (Opened)"
                    self.add_location(room_name, PlayerLocation(itemloc_name, None, door_data.panels))
                    self.EVENT_LOC_TO_ITEM[itemloc_name] = itemloc_name
                    self.set_door_item(room_name, door_name, itemloc_name)
                else:  # door shuffle
                    # This line is duplicated from StaticLingoItems
                    if door_data.skip_item is False and door_data.event is False:
                        if door_data.group is not None and door_shuffle == 1:
                            # Grouped doors are handled differently if shuffle doors is on simple.
                            self.set_door_item(room_name, door_name, door_data.group)
                        else:
                            self.handle_non_grouped_door(room_name, door_data, world, static_logic)

                if door_data.event:
                    self.add_location(room_name, PlayerLocation(door_data.item_name, None, door_data.panels))
                    self.EVENT_LOC_TO_ITEM[door_data.item_name] = door_data.item_name + " (Opened)"
                    self.set_door_item(room_name, door_name, door_data.item_name + " (Opened)")

        # Create events for each achievement panel, so that we can determine when THE MASTER is accessible. We also
        # create events for each counting panel, so that we can determine when LEVEL 2 is accessible.
        for room_name, room_data in static_logic.PANELS_BY_ROOM.items():
            for panel_name, panel_data in room_data.items():
                if panel_data.achievement:
                    event_name = room_name + " - " + panel_name + " (Achieved)"
                    self.add_location(room_name, PlayerLocation(event_name, None,
                                                                [RoomAndPanel(room_name, panel_name)]))
                    self.EVENT_LOC_TO_ITEM[event_name] = "Mastery Achievement"

                if not panel_data.non_counting and victory_condition == 2:  # LEVEL 2
                    event_name = room_name + " - " + panel_name + " (Counted)"
                    self.add_location(room_name, PlayerLocation(event_name, None,
                                                                [RoomAndPanel(room_name, panel_name)]))
                    self.EVENT_LOC_TO_ITEM[event_name] = "Counting Panel Solved"

        # Handle the victory condition. Victory conditions other than the chosen one become regular checks, so we need
        # to prevent the actual victory condition from becoming a check.
        self.MASTERY_LOCATION = "Orange Tower Seventh Floor - THE MASTER"
        self.LEVEL_2_LOCATION = "N/A"

        if victory_condition == 0:
            self.VICTORY_CONDITION = "Orange Tower Seventh Floor - THE END"
            self.add_location("Orange Tower Seventh Floor", PlayerLocation("The End (Solved)"))
            self.EVENT_LOC_TO_ITEM["The End (Solved)"] = "Victory"
        elif victory_condition == 1:
            self.VICTORY_CONDITION = "Orange Tower Seventh Floor - THE MASTER"
            self.MASTERY_LOCATION = "Orange Tower Seventh Floor - Mastery Achievements"

            self.add_location("Orange Tower Seventh Floor", PlayerLocation(self.MASTERY_LOCATION, None, []))
            self.EVENT_LOC_TO_ITEM[self.MASTERY_LOCATION] = "Victory"
        elif victory_condition == 2:
            self.VICTORY_CONDITION = "Second Room - LEVEL 2"
            self.LEVEL_2_LOCATION = "Second Room - Unlock Level 2"

            self.add_location("Second Room", PlayerLocation(self.LEVEL_2_LOCATION, None,
                                                            [RoomAndPanel("Second Room", "LEVEL 2")]))
            self.EVENT_LOC_TO_ITEM[self.LEVEL_2_LOCATION] = "Victory"

        # Instantiate all real locations.
        location_classification = LocationClassification.normal
        if getattr(world.multiworld, "location_checks")[world.player] == 1:
            location_classification = LocationClassification.reduced
        elif getattr(world.multiworld, "location_checks")[world.player] == 2:
            location_classification = LocationClassification.insanity

        for location_name, location_data in static_locat.ALL_LOCATION_TABLE.items():
            if location_name != self.VICTORY_CONDITION:
                if location_classification not in location_data.classification:
                    continue

                self.add_location(location_data.room, PlayerLocation(location_name, location_data.code,
                                                                     location_data.panels))
                self.REAL_LOCATIONS.append(location_name)

        # Instantiate all real items.
        for name, item in static_items.ALL_ITEM_TABLE.items():
            if item.should_include(world):
                self.REAL_ITEMS.append(name)

        # Create the paintings mapping, if painting shuffle is on.
        if painting_shuffle:
            # Shuffle paintings until we get something workable.
            workable_paintings = False
            for i in range(0, 20):
                workable_paintings = self.randomize_paintings(world, static_logic)
                if workable_paintings:
                    break

            if not workable_paintings:
                raise Exception("This Lingo world was unable to generate a workable painting mapping after 20 "
                                "iterations. This is very unlikely to happen on its own, and probably indicates some "
                                "kind of logic error.")

        if door_shuffle > 0 and location_classification != LocationClassification.insanity\
                and test_options.disable_forced_good_item is False:
            # If shuffle doors is on, force a useful item onto the HI panel. This may not necessarily get you out of BK,
            # but you the goal is to allow you to reach at least one more check. The non-painting ones are hardcoded
            # right now. We only allow the entrance to the Pilgrim Room if color shuffle is off, because otherwise there
            # are no extra checks in there. We only include the entrance to the Rhyme Room when color shuffle is off and
            # door shuffle is on simple, because otherwise there are no extra checks in there.
            good_item_options: List[str] = ["Starting Room - Back Right Door"]

            if not color_shuffle:
                good_item_options.append("Pilgrim Room - Sun Painting")

            if door_shuffle == 1:
                good_item_options += ["Entry Doors", "Welcome Back Doors"]

                if not color_shuffle:
                    good_item_options.append("Rhyme Room Doors")
            else:
                good_item_options += ["Starting Room - Main Door", "Welcome Back Area - Shortcut to Starting Room"]

            for painting_obj in static_logic.PAINTINGS_BY_ROOM["Starting Room"]:
                if not painting_obj.enter_only or painting_obj.required_door is None:
                    continue

                # If painting shuffle is on, we only want to consider paintings that actually go somewhere.
                if painting_shuffle and painting_obj.id not in self.PAINTING_MAPPING.keys():
                    continue

                pdoor = static_logic.DOORS_BY_ROOM[painting_obj.required_door.room][painting_obj.required_door.door]
                good_item_options.append(pdoor.item_name)

            # Copied from The Witness -- remove any plandoed items from the possible good items set.
            for v in world.multiworld.plando_items[world.player]:
                if v.get("from_pool", True):
                    for item_key in {"item", "items"}:
                        if item_key in v:
                            if type(v[item_key]) is str:
                                if v[item_key] in good_item_options:
                                    good_item_options.remove(v[item_key])
                            elif type(v[item_key]) is dict:
                                for item, weight in v[item_key].items():
                                    if weight and item in good_item_options:
                                        good_item_options.remove(item)
                            else:
                                # Other type of iterable
                                for item in v[item_key]:
                                    if item in good_item_options:
                                        good_item_options.remove(item)

            if len(good_item_options) > 0:
                self.FORCED_GOOD_ITEM = world.random.choice(good_item_options)
                self.REAL_ITEMS.remove(self.FORCED_GOOD_ITEM)
                self.REAL_LOCATIONS.remove("Starting Room - HI")

    def randomize_paintings(self, world: World, static_logic: StaticLingoLogic) -> bool:
        self.PAINTING_MAPPING.clear()

        door_shuffle = getattr(world.multiworld, "shuffle_doors")[world.player]

        # Determine the set of exit paintings. All required-exit paintings are included, as are all
        # required-when-no-doors paintings if door shuffle is off. We then fill the set with random other paintings.
        chosen_exits = []
        if door_shuffle == 0:
            chosen_exits = [painting_id for painting_id, painting in static_logic.PAINTINGS.items()
                            if painting.required_when_no_doors]
        chosen_exits += [painting_id for painting_id, painting in static_logic.PAINTINGS.items()
                         if painting.exit_only and painting.required]
        exitable = [painting_id for painting_id, painting in static_logic.PAINTINGS.items()
                    if not painting.enter_only and not painting.disable and not painting.required]
        chosen_exits += world.random.sample(exitable, static_logic.PAINTING_EXITS - len(chosen_exits))

        # Determine the set of entrance paintings.
        enterable = [painting_id for painting_id, painting in static_logic.PAINTINGS.items()
                     if not painting.exit_only and not painting.disable and painting_id not in chosen_exits]
        chosen_entrances = world.random.sample(enterable, static_logic.PAINTING_ENTRANCES)

        # Create a mapping from entrances to exits.
        for warp_exit in chosen_exits:
            warp_enter = world.random.choice(chosen_entrances)

            # Check whether this is a warp from a required painting room to another (or the same) required painting
            # room. This could cause a cycle that would make certain regions inaccessible.
            warp_exit_room = static_logic.PAINTINGS[warp_exit].room
            warp_enter_room = static_logic.PAINTINGS[warp_enter].room

            required_painting_rooms = static_logic.REQUIRED_PAINTING_ROOMS
            if door_shuffle == 0:
                required_painting_rooms += static_logic.REQUIRED_PAINTING_WHEN_NO_DOORS_ROOMS

            if warp_exit_room in required_painting_rooms and warp_enter_room in required_painting_rooms:
                # This shuffling is non-workable. Start over.
                return False

            chosen_entrances.remove(warp_enter)
            self.PAINTING_MAPPING[warp_enter] = warp_exit

        for warp_enter in chosen_entrances:
            warp_exit = world.random.choice(chosen_exits)
            self.PAINTING_MAPPING[warp_enter] = warp_exit

        # The Eye Wall painting is unique in that it is both double-sided and also enter only (because it moves).
        # There is only one eligible double-sided exit painting, which is the vanilla exit for this warp. If the
        # exit painting is an entrance in the shuffle, we will disable the Eye Wall painting. Otherwise, Eye Wall
        # is forced to point to the vanilla exit.
        if "eye_painting_2" not in self.PAINTING_MAPPING.keys():
            self.PAINTING_MAPPING["eye_painting"] = "eye_painting_2"

        # Just for sanity's sake, ensure that all required painting rooms are accessed.
        for painting_id, painting in static_logic.PAINTINGS.items():
            if painting_id not in self.PAINTING_MAPPING.values()\
                    and (painting.required or (painting.required_when_no_doors and door_shuffle == 0)):
                return False

        return True
