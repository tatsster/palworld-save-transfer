import os
import json
import sys
import yaml

from lib.gvas import GvasFile
from lib.noindent import CustomEncoder
from lib.palsav import compress_gvas_to_sav, decompress_sav_to_gvas
from lib.paltypes import PALWORLD_CUSTOM_PROPERTIES, PALWORLD_TYPE_HINTS


def main():
    if len(sys.argv) < 2:
        print('save_transfer.py <guidance_file>')
        exit(1)

    # Warn the user about potential data loss.
    print('WARNING: Running this script WILL change your save files and could \
potentially corrupt your data. It is HIGHLY recommended that you make a backup \
of your save folder before continuing. Press enter if you would like to continue.')
    input('> ')

    guidance_file = sys.argv[1]
    working_path = os.path.dirname(os.path.abspath(guidance_file))

    old_server = ''
    new_server = ''
    old_guid = ''
    new_guid = ''
    with open(guidance_file, 'r') as file:
        guidance_file = yaml.safe_load(file)
        old_server = guidance_file["SOURCE_SERVER"]
        new_server = guidance_file["DEST_SERVER"]
        old_guid = guidance_file["SOURCE_PLAYER"]
        new_guid = guidance_file["DEST_PLAYER"]

    # Apply expected formatting for the GUID.
    new_guid_formatted = '{}-{}-{}-{}-{}'.format(
        new_guid[:8], new_guid[8:12], new_guid[12:16], new_guid[16:20], new_guid[20:]).lower()

    # Create path for .sav
    old_level_sav_path = os.path.join(working_path, old_server, "Level.sav")
    new_level_sav_path = os.path.join(working_path, new_server, "Level.sav")
    old_sav_path = os.path.join(
        working_path, old_server, "Players", old_guid + '.sav')
    new_sav_path = os.path.join(
        working_path, new_server, "Players", new_guid + '.sav')

    # Create path for .sav.json
    old_level_json_path = old_level_sav_path + '.json'
    new_level_json_path = new_level_sav_path + '.json'
    old_json_path = old_sav_path + '.json'
    new_json_path = new_sav_path + '.json'

    # Check exist
    if not os.path.exists(old_level_sav_path) or not os.path.isfile(old_level_sav_path):
        print(f"{old_level_sav_path} does not exist")
        exit(1)
    if not os.path.exists(new_level_sav_path) or not os.path.isfile(new_level_sav_path):
        print(f"{new_level_sav_path} does not exist")
        exit(1)
    if not os.path.exists(old_sav_path) or not os.path.isfile(old_sav_path):
        print(f"{old_sav_path} does not exist")
        exit(1)
    if not os.path.exists(new_sav_path) or not os.path.isfile(new_sav_path):
        print(f"{new_sav_path} does not exist")
        exit(1)

    # Convert to Json
    convert_sav_to_json(old_level_sav_path, old_level_json_path, False)
    convert_sav_to_json(new_level_sav_path, new_level_json_path, False)
    convert_sav_to_json(old_sav_path, old_json_path, False)
    convert_sav_to_json(new_sav_path, new_json_path, False)
    print("Converted save files to JSON")

    # Parse our JSON files.
    with open(old_json_path, "r", encoding="utf8") as f:
        old_json = json.load(f)
    with open(old_level_json_path, "r", encoding="utf8") as f:
        old_level_json = json.load(f)
    with open(new_json_path, "r", encoding="utf8") as f:
        new_json = json.load(f)
    with open(new_level_json_path, "r", encoding="utf8") as f:
        new_level_json = json.load(f)
    print('JSON files have been parsed')

    # Player data replacement
    old_json["properties"]["SaveData"]["value"]["PlayerUId"]["value"] = new_guid_formatted
    old_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["PlayerUId"]["value"] = new_guid_formatted

    # Get old & new InstanceId
    old_instance_id = old_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"]
    new_instance_id = new_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"]

    # ! Get Pal info in CharacterContainerSaveData
    OtomoCharacterContainerId = old_json["properties"]["SaveData"]["value"][
        "OtomoCharacterContainerId"]["value"]["ID"]["value"]
    PalStorageContainerId = old_json["properties"]["SaveData"]["value"][
        "PalStorageContainerId"]["value"]["ID"]["value"]

    # Get Level data from old
    instance_ids_len = len(
        old_level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"])
    playerData = None
    palsData = []
    for i in range(instance_ids_len):
        current_char_save = old_level_json["properties"]["worldSaveData"]["value"][
            "CharacterSaveParameterMap"]["value"][i]
        instance_id = current_char_save["key"]["InstanceId"]["value"]
        # This is player
        if instance_id == old_instance_id:
            playerData = current_char_save
            playerData["key"]["PlayerUId"]["value"] = new_guid_formatted
        else:
            playerUId = current_char_save["key"]["PlayerUId"]["value"]
            # This is pals
            if playerUId == "00000000-0000-0000-0000-000000000000":
                Slot_ContainerId = current_char_save["value"]["RawData"]["value"][
                    "object"]["SaveParameter"]["value"]["SlotID"]["value"][
                    "ContainerId"]["value"]["ID"]["value"]
                if (Slot_ContainerId == OtomoCharacterContainerId or
                        Slot_ContainerId == PalStorageContainerId):
                    palsData.append(current_char_save)

    # ! Overwrite playerData to Level - CharacterSaveParameterMap
    instance_ids_len = len(
        new_level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"])
    for i in range(instance_ids_len):
        instance_id = new_level_json["properties"]["worldSaveData"]["value"][
            "CharacterSaveParameterMap"]["value"][i]["key"]["InstanceId"]["value"]
        if instance_id == new_instance_id:
            new_level_json["properties"]["worldSaveData"]["value"][
                "CharacterSaveParameterMap"]["value"][i] = playerData
            break

    # ! Append pals to Level - CharacterSaveParameterMap
    for i in range(len(palsData)):
        new_level_json["properties"]["worldSaveData"]["value"][
            "CharacterSaveParameterMap"]["value"].append(palsData[i])

    # Get Pal info in CharacterContainerSaveData
    old_char_save_len = len(
        old_level_json["properties"]["worldSaveData"]["value"]["CharacterContainerSaveData"]["value"])
    target_char_save = []
    for i in range(old_char_save_len):
        char_save = old_level_json["properties"]["worldSaveData"]["value"][
            "CharacterContainerSaveData"]["value"][i]
        char_save_id = char_save["key"]["ID"]["value"]
        if char_save_id == OtomoCharacterContainerId or char_save_id == PalStorageContainerId:
            target_char_save.append(char_save)

    # ! Append CharacterContainerSaveData from old Level to new
    for i in range(len(target_char_save)):
        new_level_json["properties"]["worldSaveData"]["value"][
            "CharacterContainerSaveData"]["value"].append(target_char_save[i])

    # Get item info UId in ItemContainerSaveData
    CommonContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["CommonContainerId"]["value"]["ID"]["value"]
    DropSlotContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["DropSlotContainerId"]["value"]["ID"]["value"]
    EssentialContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["EssentialContainerId"]["value"]["ID"]["value"]
    WeaponLoadOutContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["WeaponLoadOutContainerId"]["value"]["ID"]["value"]
    PlayerEquipArmorContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["PlayerEquipArmorContainerId"]["value"]["ID"]["value"]
    FoodEquipContainerId = old_json["properties"]["SaveData"]["value"][
        "inventoryInfo"]["value"]["FoodEquipContainerId"]["value"]["ID"]["value"]

    old_invent_save_len = len(old_level_json["properties"]["worldSaveData"]
                              ["value"]["ItemContainerSaveData"]["value"])
    target_invent_save = []
    for i in range(old_invent_save_len):
        inventory_save = old_level_json["properties"]["worldSaveData"]["value"][
            "ItemContainerSaveData"]["value"][i]
        invent_save_id = inventory_save["key"]["ID"]["value"]
        if (invent_save_id == CommonContainerId or
                invent_save_id == DropSlotContainerId or
                invent_save_id == EssentialContainerId or
                invent_save_id == WeaponLoadOutContainerId or
                invent_save_id == PlayerEquipArmorContainerId or
                invent_save_id == FoodEquipContainerId):
            target_invent_save.append(inventory_save)

    # ! Append CharacterContainerSaveData from old Level to new
    for i in range(len(target_invent_save)):
        new_level_json["properties"]["worldSaveData"]["value"]["ItemContainerSaveData"]["value"].append(target_invent_save[i])
    print('Changes have been made')

    #  Dump modified data to JSON
    with open(new_json_path, "w", encoding="utf8") as f:
        json.dump(old_json, f, indent="\t", cls=CustomEncoder)
    with open(new_level_json_path, "w", encoding="utf8") as f:
        json.dump(new_level_json, f, indent="\t", cls=CustomEncoder)
    print("JSON files have been exported")

    # Convert our JSON files to save files.
    convert_json_to_sav(new_level_json_path, new_level_sav_path)
    convert_json_to_sav(new_json_path, new_sav_path)
    print('Converted JSON files back to save files')

    # Clean up miscellaneous GVAS and JSON files which are no longer needed.
    clean_up_files(old_level_sav_path)
    # clean_up_files(old_sav_path)
    clean_up_files(new_level_sav_path)
    # clean_up_files(new_sav_path)
    print('Miscellaneous files removed')

    print('Fix has been applied! Have fun!')

def convert_sav_to_json(filename, output_path, minify):
    print(f"Converting {filename} to JSON, saving to {output_path}")
    if os.path.exists(output_path):
        print(f"{output_path} already exists, this will overwrite the file")
    print(f"Decompressing sav file")
    with open(filename, "rb") as f:
        data = f.read()
        raw_gvas, _ = decompress_sav_to_gvas(data)
    print(f"Loading GVAS file")
    gvas_file = GvasFile.read(
        raw_gvas, PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES)
    print(f"Writing JSON to {output_path}")
    with open(output_path, "w", encoding="utf8") as f:
        indent = None if minify else "\t"
        json.dump(gvas_file.dump(), f, indent=indent, cls=CustomEncoder)


def convert_json_to_sav(filename, output_path):
    print(f"Converting {filename} to SAV, saving to {output_path}")
    if os.path.exists(output_path):
        print(f"{output_path} already exists, this will overwrite the file")

    print(f"Loading JSON from {filename}")
    with open(filename, "r", encoding="utf8") as f:
        data = json.load(f)
    gvas_file = GvasFile.load(data)
    print(f"Compressing SAV file")
    if (
        "Pal.PalWorldSaveGame" in gvas_file.header.save_game_class_name
        or "Pal.PalLocalWorldSaveGame" in gvas_file.header.save_game_class_name
    ):
        save_type = 0x32
    else:
        save_type = 0x31
    sav_file = compress_gvas_to_sav(
        gvas_file.write(PALWORLD_CUSTOM_PROPERTIES), save_type
    )
    print(f"Writing SAV file to {output_path}")
    with open(output_path, "wb") as f:
        f.write(sav_file)


def clean_up_files(file):
    os.remove(file + '.json')

if __name__ == "__main__":
    main()