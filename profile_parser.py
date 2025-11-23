

class ProfileParser:
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):
        output = {}
        with open(self.filepath, 'r') as file:
            current_block = {}
            block_type = None

            for line in file:
                line = line.strip()
                if line.startswith(';') or line.startswith("#") or line == '':
                    continue
                if line.startswith('[') and line.endswith(']'):
                    if block_type != None:
                        if block_type == "vendor":
                            output['vendor'] = current_block
                        else:
                            if block_type not in output:
                                output[block_type] = []
                            output[block_type].append(current_block)
                        current_block = {}

                    if "vendor" in line:
                        block_type = "vendor"
                    else: 
                        block_type = line[1:-1].split(":")[0].strip()
                        current_block['name'] = line[1:-1].split(":")[1].strip()

                elif '=' in line:
                    key, value = line.split('=', 1)
                    value = value.strip()

                    # ; array value parsing
                    if key.strip() in ["default_materials"]:
                        value = [v.strip() for v in value.split(';')]

                    current_block[key.strip()] = value
            
            # Don't forget to save the last block
            if block_type != None:
                if block_type == "vendor":
                    output['vendor'] = current_block
                else:
                    if block_type not in output:
                        output[block_type] = []
                    output[block_type].append(current_block)

        return output