import json
import os
import subprocess
import sys
import zlib
import yaml

UESAVE_TYPE_MAPS = [
    ".worldSaveData.CharacterSaveParameterMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.Key=Struct",
    ".worldSaveData.FoliageGridSaveDataMap.ModelMap.InstanceDataMap.Key=Struct",
    ".worldSaveData.MapObjectSpawnerInStageSaveData.Key=Struct",
    ".worldSaveData.ItemContainerSaveData.Key=Struct",
    ".worldSaveData.CharacterContainerSaveData.Key=Struct",
]


def main():
    if len(sys.argv) < 3:
        print('save-tranfer.py <uesave.exe> <guide_file>')
        exit(1)

    # Warn the user about potential data loss.
    print('WARNING: Running this script WILL change your save files and could \
potentially corrupt your data. It is HIGHLY recommended that you make a backup \
of your save folder before continuing. Press enter if you would like to continue.')
    input('> ')

    uesave_path = sys.argv[1]
    guide_file = sys.argv[2]

    working_path = os.path.dirname(os.path.abspath(guide_file))

    old_server = ''
    new_server = ''
    old_guid = ''
    new_guid = ''
    with open(guide_file, 'r') as file:
        guide_file = yaml.safe_load(file)
        old_server = guide_file["SOURCE_SERVER"]
        new_server = guide_file["DEST_SERVER"]
        old_guid = guide_file["SOURCE_PLAYER"]
        new_guid = guide_file["DEST_PLAYER"]

    # Apply expected formatting for the GUID.
    new_guid_formatted = '{}-{}-{}-{}-{}'.format(
        new_guid[:8], new_guid[8:12], new_guid[12:16], new_guid[16:20], new_guid[20:]).lower()
    old_level_formatted = ''
    new_level_formatted = ''

    # Player GUIDs in a guild are stored as the decimal representation of their GUID.
    # Every byte in decimal represents 2 hexidecimal characters of the GUID
    # 32-bit little endian.
    for y in range(8, 36, 8):
        for x in range(y-1, y-9, -2):
            temp_old = str(int(old_guid[x-1] + old_guid[x], 16))+',\n'
            temp_new = str(int(new_guid[x-1] + new_guid[x], 16))+',\n'
            old_level_formatted += temp_old
            new_level_formatted += temp_new

    old_level_formatted = old_level_formatted.rstrip("\n,")
    new_level_formatted = new_level_formatted.rstrip("\n,")
    old_level_formatted = list(map(int, old_level_formatted.split(",\n")))
    new_level_formatted = list(map(int, new_level_formatted.split(",\n")))

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

    # uesave_path must point directly to the executable, not just the path it is located in.
    if not os.path.exists(uesave_path) or not os.path.isfile(uesave_path):
        print('ERROR: Your given <uesave_path> of "' + uesave_path +
              '" is invalid. It must point directly to the executable. For example: C:\\Users\\Bob\\.cargo\\bin\\uesave.exe')
        exit(1)

    # save_path must exist in order to use it.
    if not os.path.exists(old_level_sav_path) or not os.path.exists(new_level_sav_path):
        print('ERROR: Your given <SOURCE_SERVER> or <DEST_SERVER>' +
              '" does not exist. Did you enter the correct path to your save folder?')
        exit(1)

    # The player needs to have created a character on the dedicated server and that save is used for this script.
    if not os.path.exists(new_sav_path) or not os.path.exists(old_sav_path):
        print('ERROR: Your player save does not exist. Did you enter the correct new GUID of your player? It should look like "8E910AC2000000000000000000000000".\nDid your player create their character with the provided save? Once they create their character, a file called "' +
              new_sav_path + '" should appear. Look back over the steps in the README on how to get your new GUID.')
        exit(1)

    # Convert save files to JSON so it is possible to edit them.
    sav_to_json(uesave_path, old_level_sav_path)
    sav_to_json(uesave_path, old_sav_path)
    sav_to_json(uesave_path, new_level_sav_path)
    sav_to_json(uesave_path, new_sav_path)
    print('Converted save files to JSON')

    # Parse our JSON files.
    with open(old_json_path) as f:
        old_json = json.load(f)
    with open(old_level_json_path) as f:
        old_level_json = json.load(f)
    with open(new_json_path) as f:
        new_json = json.load(f)
    with open(new_level_json_path) as f:
        new_level_json = json.load(f)
    print('JSON files have been parsed')

    # Replace all instances of the old GUID with the new GUID.

    # Player data replacement.
    old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
    old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"]["IndividualId"][
        "Struct"]["value"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
    # Get old & new InstanceId
    old_instance_id = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "IndividualId"]["Struct"]["value"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]
    new_instance_id = new_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "IndividualId"]["Struct"]["value"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]

    # Get Level data from old.
    instance_ids_len = len(old_level_json["root"]["properties"]["worldSaveData"]
                           ["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"]["Map"]["value"])
    playerData = None
    for i in range(instance_ids_len):
        instance_id = old_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"][
            "CharacterSaveParameterMap"]["Map"]["value"][i]["key"]["Struct"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]
        if instance_id == old_instance_id:
            playerData = old_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"][
                "Map"]["value"][i]
            break

    # ! Overwrite Level data to new CharacterSaveParameterMap
    instance_ids_len = len(new_level_json["root"]["properties"]["worldSaveData"]
                           ["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"]["Map"]["value"])
    for i in range(instance_ids_len):
        instance_id = new_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"][
            "CharacterSaveParameterMap"]["Map"]["value"][i]["key"]["Struct"]["Struct"]["InstanceId"]["Struct"]["value"]["Guid"]
        if instance_id == new_instance_id:
            new_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"][
                "Map"]["value"][i] = playerData
            new_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"]["CharacterSaveParameterMap"][
                "Map"]["value"][i]["key"]["Struct"]["Struct"]["PlayerUId"]["Struct"]["value"]["Guid"] = new_guid_formatted
            break

    # ! Get Pal info in CharacterContainerSaveData
    OtomoCharacterContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "OtomoCharacterContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    PalStorageContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "PalStorageContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    
    old_char_save_len = len(old_level_json["root"]["properties"]["worldSaveData"]
                            ["Struct"]["value"]["Struct"]["CharacterContainerSaveData"]["Map"]["value"])
    target_char_save = []
    for i in range(old_char_save_len):
        char_save = old_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"][
            "CharacterContainerSaveData"]["Map"]["value"][i]
        char_save_id = char_save["key"]["Struct"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
        if char_save_id == OtomoCharacterContainerId or char_save_id == PalStorageContainerId:
            target_char_save.append(char_save)
    
    # Append CharacterContainerSaveData from old Level to new
    new_char_save_len = len(new_level_json["root"]["properties"]["worldSaveData"]
                            ["Struct"]["value"]["Struct"]["CharacterContainerSaveData"]["Map"]["value"])
    for i in range(len(target_char_save)):
        new_level_json["root"]["properties"]["worldSaveData"][
            "Struct"]["value"]["Struct"]["CharacterContainerSaveData"]["Map"]["value"].append(target_char_save[i])
    

    # ! Get item info in ItemContainerSaveData
    CommonContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["CommonContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    DropSlotContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["DropSlotContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    EssentialContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["EssentialContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    WeaponLoadOutContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["WeaponLoadOutContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    PlayerEquipArmorContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["PlayerEquipArmorContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    FoodEquipContainerId = old_json["root"]["properties"]["SaveData"]["Struct"]["value"]["Struct"][
        "inventoryInfo"]["Struct"]["value"]["Struct"]["FoodEquipContainerId"]["Struct"]["value"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
    
    old_invent_save_len = len(old_level_json["root"]["properties"]["worldSaveData"]
                            ["Struct"]["value"]["Struct"]["ItemContainerSaveData"]["Map"]["value"])
    target_invent_save = []
    for i in range(old_invent_save_len):
        inventory_save = old_level_json["root"]["properties"]["worldSaveData"]["Struct"]["value"]["Struct"][
            "ItemContainerSaveData"]["Map"]["value"][i]
        invent_save_id = inventory_save["key"]["Struct"]["Struct"]["ID"]["Struct"]["value"]["Guid"]
        if (invent_save_id == CommonContainerId or 
                invent_save_id == DropSlotContainerId or 
                invent_save_id == EssentialContainerId or
                invent_save_id == WeaponLoadOutContainerId or
                invent_save_id == PlayerEquipArmorContainerId or
                invent_save_id == FoodEquipContainerId):
            target_invent_save.append(inventory_save)
    
    # Append CharacterContainerSaveData from old Level to new
    new_invent_save_len = len(new_level_json["root"]["properties"]["worldSaveData"]
                            ["Struct"]["value"]["Struct"]["ItemContainerSaveData"]["Map"]["value"])
    for i in range(len(target_invent_save)):
        new_level_json["root"]["properties"]["worldSaveData"][
            "Struct"]["value"]["Struct"]["ItemContainerSaveData"]["Map"]["value"].append(target_invent_save[i])

    print('Changes have been made')

    # Dump modified data to JSON.
    # Change on old .sav.json -> Dump to new .sav.json
    with open(new_json_path, 'w') as f:
        json.dump(old_json, f, indent=2)
    with open(new_level_json_path, 'w') as f:
        json.dump(new_level_json, f, indent=2)
    print('JSON files have been exported')

    # Convert our JSON files to save files.
    json_to_sav(uesave_path, new_level_json_path)
    json_to_sav(uesave_path, new_json_path)
    print('Converted JSON files back to save files')

    # Clean up miscellaneous GVAS and JSON files which are no longer needed.
    clean_up_files(old_level_sav_path)
    # clean_up_files(old_sav_path)
    clean_up_files(new_level_sav_path)
    # clean_up_files(new_sav_path)
    print('Miscellaneous files removed')

    print('Fix has been applied! Have fun!')

def sav_to_json(uesave_path, file):
    with open(file, 'rb') as f:
        # Read the file
        data = f.read()
        uncompressed_len = int.from_bytes(data[0:4], byteorder='little')
        compressed_len = int.from_bytes(data[4:8], byteorder='little')
        magic_bytes = data[8:11]
        save_type = data[11]
        # Check for magic bytes
        if magic_bytes != b'PlZ':
            print(f'File {file} is not a save file, found {magic_bytes} instead of P1Z')
            return
        # Valid save types
        if save_type not in [0x30, 0x31, 0x32]:
            print(f'File {file} has an unknown save type: {save_type}')
            return
        # We only have 0x31 (single zlib) and 0x32 (double zlib) saves
        if save_type not in [0x31, 0x32]:
            print(f'File {file} uses an unhandled compression type: {save_type}')
            return
        if save_type == 0x31:
            # Check if the compressed length is correct
            if compressed_len != len(data) - 12:
                print(f'File {file} has an incorrect compressed length: {compressed_len}')
                return
        # Decompress file
        uncompressed_data = zlib.decompress(data[12:])
        if save_type == 0x32:
            # Check if the compressed length is correct
            if compressed_len != len(uncompressed_data):
                print(f'File {file} has an incorrect compressed length: {compressed_len}')
                return
            # Decompress file
            uncompressed_data = zlib.decompress(uncompressed_data)
        # Check if the uncompressed length is correct
        if uncompressed_len != len(uncompressed_data):
            print(f'File {file} has an incorrect uncompressed length: {uncompressed_len}')
            return
        # Save the uncompressed file
        with open(file + '.gvas', 'wb') as f:
            f.write(uncompressed_data)
        print(f'File {file} uncompressed successfully')
        # Convert to json with uesave
        # Run uesave.exe with the uncompressed file piped as stdin
        # Standard out will be the json string
        uesave_run = subprocess.run(uesave_to_json_params(uesave_path, file+'.json'), input=uncompressed_data, capture_output=True)
        # Check if the command was successful
        if uesave_run.returncode != 0:
            print(f'uesave.exe failed to convert {file} (return {uesave_run.returncode})')
            print(uesave_run.stdout.decode('utf-8'))
            print(uesave_run.stderr.decode('utf-8'))
            return
        print(f'File {file} (type: {save_type}) converted to JSON successfully')

def json_to_sav(uesave_path, file):
    # Convert the file back to binary
    gvas_file = file.replace('.sav.json', '.sav.gvas')
    sav_file = file.replace('.sav.json', '.sav')
    uesave_run = subprocess.run(uesave_from_json_params(uesave_path, file, gvas_file))
    if uesave_run.returncode != 0:
        print(f'uesave.exe failed to convert {file} (return {uesave_run.returncode})')
        return
    # Open the old sav file to get type
    with open(sav_file, 'rb') as f:
        data = f.read()
        save_type = data[11]
    # Open the binary file
    with open(gvas_file, 'rb') as f:
        # Read the file
        data = f.read()
        uncompressed_len = len(data)
        compressed_data = zlib.compress(data)
        compressed_len = len(compressed_data)
        if save_type == 0x32:
            compressed_data = zlib.compress(compressed_data)
        with open(sav_file, 'wb') as f:
            f.write(uncompressed_len.to_bytes(4, byteorder='little'))
            f.write(compressed_len.to_bytes(4, byteorder='little'))
            f.write(b'PlZ')
            f.write(bytes([save_type]))
            f.write(bytes(compressed_data))
    print(f'Converted {file} to {sav_file}')

def clean_up_files(file):
    os.remove(file + '.json')
    os.remove(file + '.gvas')

def uesave_to_json_params(uesave_path, out_path):
    args = [
        uesave_path,
        'to-json',
        '--output', out_path,
    ]
    for map_type in UESAVE_TYPE_MAPS:
        args.append('--type')
        args.append(f'{map_type}')
    return args

def uesave_from_json_params(uesave_path, input_file, output_file):
    args = [
        uesave_path,
        'from-json',
        '--input', input_file,
        '--output', output_file,
    ]
    return args

if __name__ == "__main__":
    main()
