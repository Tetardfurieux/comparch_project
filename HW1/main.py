import json
import sys
import copy

from json import JSONEncoder

class MyEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

class Intruction:
    def __init__(self, mnemonic, dest, opA, opB):
        self.mnemonic = mnemonic
        self.dest: int = dest
        self.opA: int = opA
        self.opB: int = opB
    
    def __str__(self):
        return f"{self.mnemonic} {self.dest} {self.opA} {self.opB}"

class Instructioni:
    def __init__(self, mnemonic, dest, opA, imm):
        self.mnemonic = mnemonic
        self.dest: int = dest
        self.opA: int = opA
        self.imm: int = imm

    def __str__(self):
        return f"{self.mnemonic} {self.dest} {self.opA} {self.imm}"

class IntegerQueueEntry:
    def __init__(self, DestRegister, OpAIsReady, OpARegTag, OpAValue, OpBIsReady, OpBRegTag, OpBValue, OpCode, PC):
        self.DestRegister = DestRegister
        self.OpAIsReady = OpAIsReady
        self.OpARegTag = OpARegTag
        self.OpAValue = OpAValue
        self.OpBIsReady = OpBIsReady
        self.OpBRegTag = OpBRegTag
        self.OpBValue = OpBValue
        self.OpCode = OpCode
        self.PC = PC

    def toJSON(self):
        return {
            "DestRegister": self.DestRegister,
            "OpAIsReady": self.OpAIsReady,
            "OpARegTag": self.OpARegTag,
            "OpAValue": self.OpAValue,
            "OpBIsReady": self.OpBIsReady,
            "OpBRegTag": self.OpBRegTag,
            "OpBValue": self.OpBValue,
            "OpCode": self.OpCode,
            "PC": self.PC
        }

    def copy(self):
        return IntegerQueueEntry(self.DestRegister, self.OpAIsReady, self.OpARegTag,
                                 self.OpAValue, self.OpBIsReady, self.OpBRegTag,
                                 self.OpBValue, self.OpCode, self.PC)

    def __str__(self):
        return f"{self.DestRegister} {self.OpAIsReady} {self.OpARegTag} {self.OpAValue} {self.OpBIsReady} {self.OpBRegTag} {self.OpBValue} {self.OpCode} {self.PC}"
    
class ActiveListEntry:
    def __init__(self, Done, Exception, LogicalDestination, OldDestination, PC):
        self.Done = Done
        self.Exception = Exception
        self.LogicalDestination = LogicalDestination
        self.OldDestination = OldDestination
        self.PC = PC

    def toJSON(self):
        return {
            "Done": self.Done,
            "Exception": self.Exception,
            "LogicalDestination": self.LogicalDestination,
            "OldDestination": self.OldDestination,
            "PC": self.PC
        }

    def __str__(self):
        return f"{self.Done} {self.Exception} {self.LogicalDestination} {self.OldDestination} {self.PC}"

class ProcessorState:
    def __init__(self, NextState, Instructions):
        # Initialize data structures
        self.PC = 0
        self.PhysicalRegisterFile = [0] * 64
        self.DecodedPCs = []
        self.Exception = False
        self.ExceptionPC = 0
        self.RegisterMapTable = list(range(32))
        self.FreeList = list(range(32, 64))
        self.BusyBitTable = [False] * 64
        self.ActiveList = []
        self.IntegerQueue = []
        self.Log = []
        self.NextState: ProcessorState = NextState
        self.Backpressure = False
        self.Instructions = Instructions
        self.ALUs = [[None, None], [None, None], [None, None], [None, None]]
    
    def toJSON(self):
        return {
            "PC": self.PC,
            "PhysicalRegisterFile": self.PhysicalRegisterFile,
            "DecodedPCs": self.DecodedPCs,
            "Exception": self.Exception,
            "ExceptionPC": self.ExceptionPC,
            "RegisterMapTable": self.RegisterMapTable,
            "FreeList": self.FreeList,
            "BusyBitTable": self.BusyBitTable,
            "ActiveList": self.ActiveList,
            "IntegerQueue": self.IntegerQueue,
        }
    def dumpStateIntoLog(self, cycle):
        # Create dictionary to represent state
        '''state_dict = {
            "PC": self.PC,
            "PhysicalRegisterFile": self.PhysicalRegisterFile,
            "DecodedPCs": self.DecodedPCs,
            "Exception": self.Exception,
            "ExceptionPC": self.ExceptionPC,
            "RegisterMapTable": self.RegisterMapTable,
            "FreeList": self.FreeList,
            "BusyBitTable": self.BusyBitTable,
            "ActiveList": self.ActiveList,
            "IntegerQueue": self.IntegerQueue
        }   '''
        state_dict = self.toJSON()
        self.NextState.Log.append(state_dict)
        # Output state to JSON file
        #print(self.Log)
        with open(f"cycle_{cycle}.json", "w") as f:
            json.dump(state_dict, f, indent=4, cls=MyEncoder)
    

    def activeListIsEmpty(self):
        return len(self.ActiveList) == 0 and self.Exception == False

    # First stage of ALU
    def execute1(self):
        for i, ALU in enumerate(self.ALUs):
            if ALU[0] is None:
                continue            
            instruction = ALU[0]
            ALU_state_2 = instruction.copy()
            # Execute the instruction
            # OpAIsReady is the Exception
            # OpAValue is the result of the operation
            if instruction.OpCode == "add" or instruction.OpCode == "addi":
                ALU_state_2.OpAValue = instruction.OpAValue + instruction.OpBValue
                ALU_state_2.OpAIsReady = False

            elif instruction.OpCode == "sub":
                ALU_state_2.OpAValue = instruction.OpAValue - instruction.OpBValue
                ALU_state_2.OpAIsReady = False

            elif instruction.OpCode == "mulu":
                ALU_state_2.OpAValue = instruction.OpAValue * instruction.OpBValue
                ALU_state_2.OpAIsReady = False

            elif instruction.OpCode == "divu":
                if instruction.OpBValue == 0:
                    ALU_state_2.OpAIsReady = True # Exception
                else:
                    ALU_state_2.OpAValue = instruction.OpAValue / instruction.OpBValue
                    ALU_state_2.OpAIsReady = False

            elif instruction.OpCode == "remu":
                if instruction.OpBValue == 0:
                    ALU_state_2.OpAIsReady = True # Exception
                else:
                    ALU_state_2.OpAValue = instruction.OpAValue % instruction.OpBValue
                    ALU_state_2.OpAIsReady = False

            # Update the ALU state
            self.NextState.ALUs[i][1] = ALU_state_2
            # Clear the ALU first state (Will be filled in R&D stage)
            self.NextState.ALUs[i][0] = None 
    
    # Second stage of ALU
    def execute2(self):
        for i, ALU in enumerate(self.ALUs):
            if ALU[1] is None:
                continue
            instruction = ALU[1]
            #print("instruction: ", instruction)
            # Find the instruction in the ActiveList
            for j, entry in enumerate(self.ActiveList):
                if entry.PC == instruction.PC:
                    #print("entry found: ", entry)

                    self.NextState.ActiveList[j].Done = True
                    if instruction.OpAIsReady: # Exception
                        self.NextState.ActiveList[j].Exception = True
                        break
                    else:
                        self.NextState.ActiveList[j].Exception = False
                        self.NextState.PhysicalRegisterFile[instruction.DestRegister] = instruction.OpAValue
                        self.NextState.BusyBitTable[instruction.DestRegister] = False
                        self.NextState.ALUs[i][1] = None
                        # Forwarding path
                        self.PhysicalRegisterFile[instruction.DestRegister] = instruction.OpAValue
                        self.BusyBitTable[instruction.DestRegister] = False
                        break
                    

    def propagateFetchAndDecode(self): # Should be done
        count = 0
        if self.Exception: 
            self.NextState.PC = 0x10000
            # FLUSH DIR 4 instructions at a time from the Oldest to the Youngest
            while(len(self.DecodedPCs) - count > 0 and count < 4):
                self.NextState.DecodedPCs.pop(-1)
                count += 1
            return
        if self.Backpressure: # Next state is not ready to receive instructions
            return 
        # Fetch and decode the next instruction
        while(self.PC + count < len(self.Instructions) and count < 4):
            self.NextState.DecodedPCs.append(self.PC + count)
            self.NextState.PC += 1
            count += 1
            #print("count: ", count)
    
    def propagateRenameAndDispatch(self):
        if len(self.DecodedPCs) == 0:
            return

        remaining_instructions_count = 4 if len(self.DecodedPCs) > 3 else len(self.DecodedPCs)

        if len(self.FreeList) >= remaining_instructions_count and len(self.IntegerQueue) <= 32 - remaining_instructions_count and len(self.ActiveList) <= 32 - remaining_instructions_count:
            for _ in range(remaining_instructions_count):
                decodedPC = self.NextState.DecodedPCs.pop(0)
                # Get the instruction
                instruction = self.Instructions[decodedPC]
                # Rename the registers
                oldDest = self.RegisterMapTable[instruction.dest]
                dest = self.NextState.FreeList.pop(0)
                self.NextState.RegisterMapTable[instruction.dest] = dest
                self.NextState.BusyBitTable[dest] = True
               
               # Get the operands for the instruction and check if they are ready
                if instruction.mnemonic == "addi":
                    opB = -1 # No opB for addi
                    opBReady = True
                    opBValue = instruction.imm
                else:
                    opB = self.RegisterMapTable[instruction.opB]
                    opBReady = not self.BusyBitTable[opB]
                    opBValue = self.PhysicalRegisterFile[instruction.opB] if opBReady else 0

                opA = self.RegisterMapTable[instruction.opA]
                opAReady = not self.BusyBitTable[opA]
                opAValue = self.PhysicalRegisterFile[instruction.opA] if opAReady else 0

                #TODO: Forwarding paths
                self.RegisterMapTable[instruction.dest] = dest
                self.BusyBitTable[dest] = True
                # Create an entry in the IntegerQueue
                self.NextState.IntegerQueue.append(IntegerQueueEntry(dest, opAReady, opA, opAValue, opBReady, opB, opBValue, instruction.mnemonic, decodedPC))
                # Create an entry in the ActiveList
                self.NextState.ActiveList.append(ActiveListEntry(False, False, instruction.dest, oldDest, decodedPC))
                
        else:
            self.NextState.Backpressure = True #TODO: Next state or current state ?
        
    def propagateIssue(self):
        if self.Exception:
            return

        # Update forwarding paths
        for iq in self.IntegerQueue:
            iq.OpAIsReady = not self.BusyBitTable[iq.OpARegTag]
            iq.OpAValue = self.PhysicalRegisterFile[iq.OpARegTag] if iq.OpAIsReady else iq.OpAValue
            # No opB update for addi since it is an immediate value
            if iq.OpCode != "addi":
                iq.OpBIsReady = not self.BusyBitTable[iq.OpBRegTag] 
                iq.OpBValue = self.PhysicalRegisterFile[iq.OpBRegTag] if iq.OpBIsReady and iq.OpBIsReady != -1 else iq.OpBValue

        if len(self.IntegerQueue) <= 0:
            return

        ready_to_issue = []
        for i, entry in enumerate(self.IntegerQueue):
            if len(ready_to_issue) >= 4:
                break
            if entry.OpAIsReady and entry.OpBIsReady:
                ready_to_issue.append(i)
        
        for count, j in enumerate(ready_to_issue):
            entry = self.IntegerQueue[j]
            self.NextState.ALUs[count][0] = entry
            self.NextState.IntegerQueue.pop(j - count)
    
    def propagateALUs(self):
        self.execute2()
        self.execute1()

    def propagateCommit(self):
        if self.Exception:
            if len(self.ActiveList) == 0:
                self.NextState.Exception = False
            # Reset ALUs
            for i in range(4):
                if len(self.ALUs[i]) > 0:
                    self.NextState.ALUs[i][0] = None
                    self.NextState.ALUs[i][1] = None
            # Rollback the ActiveList 4 instructions per cycle
                tail = len(self.ActiveList) - (1+i)
                if tail >= 0:
                    entry = self.NextState.ActiveList.pop(tail)
                    self.NextState.FreeList.append(entry.OldDestination)
                    self.NextState.BusyBitTable[entry.OldDestination] = False
                    self.NextState.RegisterMapTable[entry.LogicalDestination] = entry.OldDestination

        if len(self.ActiveList) == 0:
            return

        ready_to_commit = []
        for i, entry in enumerate(self.ActiveList):
            if len(ready_to_commit) >= 4 or not entry.Done:
                break
            if entry.Exception:
                self.Exception = True
                self.ExceptionPC = entry.PC
                self.NextState.Exception = True
                self.NextState.ExceptionPC = entry.PC
                self.NextState.IntegerQueue = []
                return # Stop committing instructions

            ready_to_commit.append(i)

        for count, i in enumerate(ready_to_commit):
            # Commit the instruction
            # TODO: retiring or rolling back instructions ?
            entry = self.ActiveList[i]
            self.NextState.ActiveList.pop(i - count)
            self.ActiveList.pop(i - count)
            self.NextState.FreeList.append(entry.OldDestination)
            # Forwarding path
            self.FreeList.append(entry.OldDestination)


    def propagate(self):
        # Propagate each module
        self.propagateCommit()
        self.propagateALUs()
        self.propagateIssue()
        self.propagateRenameAndDispatch()
        self.propagateFetchAndDecode()
    
    def latch(self):
        # Advance clock
        #self.NextState.Cycle += 1
        # Latch the next state
        save = self.NextState
        self.__dict__.update(copy.deepcopy(self.NextState).__dict__)
        self.NextState = save


    def saveLog(self, output_file):
        with open(output_file, "a") as f:
            json.dump(self.NextState.Log, f, indent=4, cls=MyEncoder, sort_keys=True)
    
    def noInstruction(self):
        #print("PC: ", self.PC, " len(instructions): ", len(self.Instructions))
        return self.PC >= len(self.Instructions)

def parseInstructions(filepath):
    parsed_instructions = []
    with open(filepath, "r") as file:
        instruction_json = json.load(file)
        for instruction_str in instruction_json:
            instruction_parts = instruction_str.split()
            mnemonic = instruction_parts[0]
            dest = instruction_parts[1][:-1] # Remove the comma
            dest = dest.replace("x", "")
            opA = instruction_parts[2][:-1]  # Remove the comma
            opA = opA.replace("x", "")
            opB = instruction_parts[3]
            opB = opB.replace("x", "")
            if mnemonic == "addi":
                imm = int(instruction_parts[3])
                parsed_instructions.append(Instructioni(mnemonic, int(dest), int(opA), imm))
            else:
                parsed_instructions.append(Intruction(mnemonic, int(dest), int(opA), int(opB)))
    
    #for instr in instructions:
        #print(instr)
    return parsed_instructions

def main():

    if len(sys.argv) != 3:
        print("Usage: python main.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    

    #0. parse JSON to get the program
    instructions = parseInstructions(input_file);
    next_state = ProcessorState(None, instructions)
    current_state = ProcessorState(next_state, instructions)
    #1. dump the state of the reset system
    current_state.dumpStateIntoLog(0)
    #2. the loop for cycle-by-cycle iterations.
    i = 0
    while(not (current_state.noInstruction() and current_state.activeListIsEmpty())):
        #do propagation
        #if you have multiple modules, propagate each of them

        current_state.propagate();
        #advance clock, start next cycle
        current_state.latch();
        #dump the state
        current_state.dumpStateIntoLog(i)
        i += 1
        print(i)
    #3. save the output JSON log
    #current_state.dumpStateIntoLog(i)
    current_state.saveLog(output_file);
    

if __name__ == "__main__":
    main()


