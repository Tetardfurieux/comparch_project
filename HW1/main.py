import json
import sys
import copy

from json import JSONEncoder

# Used to serialize the objects to JSON
class MyEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__

# Class representing an instruction
class Intruction:
    def __init__(self, mnemonic, dest, opA, opB):
        self.mnemonic = mnemonic
        self.dest: int = dest
        self.opA: int = opA
        self.opB: int = opB
    
    def __str__(self):
        return f"{self.mnemonic} {self.dest} {self.opA} {self.opB}"

# Class representing an instruction with an immediate value
class Instructioni:
    def __init__(self, mnemonic, dest, opA, imm):
        self.mnemonic = mnemonic
        self.dest: int = dest
        self.opA: int = opA
        self.imm: int = imm

    def __str__(self):
        return f"{self.mnemonic} {self.dest} {self.opA} {self.imm}"

# Class representing an entry in the IntegerQueue
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

# Class representing an entry in the ActiveList
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

'''
Class representing the state of the processor with all the necessary components
The next state is the state that will be updated after the current state is propagated
'''
class ProcessorState:
    def __init__(self, NextState, Instructions):
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
        # Contains the instructions given in the input file
        self.Instructions = Instructions
        # Represents the ALUs, each ALU has 2 states 
        self.ALUs = [[None, None], [None, None], [None, None], [None, None]]
    
    # Convert the state to a JSON object
    def toJSON(self):
        return {
            "PC": self.PC,
            "PhysicalRegisterFile": self.PhysicalRegisterFile.copy(),
            "DecodedPCs": self.DecodedPCs.copy(),
            "Exception": self.Exception,
            "ExceptionPC": self.ExceptionPC,
            "RegisterMapTable": self.RegisterMapTable.copy(),
            "FreeList": self.FreeList.copy(),
            "BusyBitTable": self.BusyBitTable.copy(),
            "ActiveList": self.ActiveList.copy(),
            "IntegerQueue": self.IntegerQueue.copy(),
            "ALUs": self.ALUs.copy(),
        }
    
    # Dump the state into the log
    def dumpStateIntoLog(self):
        # Create dictionary to represent state
        state_dict = self.toJSON()
        self.NextState.Log.append(state_dict.copy())
    
    # Check if the ActiveList is empty
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
            if instruction.OpCode == "add":
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
            for j, entry in enumerate(self.NextState.ActiveList):
                if entry.PC == instruction.PC:
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
                    
    # Propagate the fetch and decode stage
    def propagateFetchAndDecode(self):
        count = 0
        if self.Exception: 
            self.NextState.PC = 0x10000
            # Flush dir 4 instructions at a time from the Oldest to the Youngest
            while(len(self.NextState.DecodedPCs) > 0 and count < 4):
                self.NextState.DecodedPCs.pop(-1)
                count += 1
            return
        if self.Backpressure: # Next state is not ready to receive instructions
            return 
        # Fetch and decode the next instruction
        while(self.NextState.PC < len(self.Instructions) and count < 4):
            self.NextState.DecodedPCs.append(self.NextState.PC)
            self.NextState.PC += 1
            count += 1
    
    # Propagate the rename and dispatch stage
    def propagateRenameAndDispatch(self):
        if len(self.DecodedPCs) <= 0 or self.Exception:
            return
        
        remaining_instructions_count = 4 if len(self.DecodedPCs) > 3 else len(self.DecodedPCs)

        # Check if there is enough space in the IntegerQueue and ActiveList, and that the FreeList contains enough registers
        freelist_is_not_empty = len(self.FreeList) >= remaining_instructions_count
        integer_queue_is_not_full = len(self.IntegerQueue) <= 32 - remaining_instructions_count
        active_list_is_not_full = len(self.ActiveList) <= 32 - remaining_instructions_count

        if freelist_is_not_empty and integer_queue_is_not_full and active_list_is_not_full:
            for _ in range(remaining_instructions_count):
                decodedPC = self.NextState.DecodedPCs.pop(0)
                # Get the instruction
                instruction = self.Instructions[decodedPC]
                opCode = instruction.mnemonic
               # Get the operands for the instruction and check if they are ready
                if instruction.mnemonic == "addi":
                    opCode = "add"
                    opB = 0 # No opB for addi
                    opBReady = True
                    opBValue = instruction.imm
                    
                else:
                    opB = self.NextState.RegisterMapTable[instruction.opB]
                    opBReady = not self.NextState.BusyBitTable[opB]
                    opBValue = self.NextState.PhysicalRegisterFile[instruction.opB] if opBReady else 0
                
                opA = self.NextState.RegisterMapTable[instruction.opA]
                opAReady = not self.NextState.BusyBitTable[opA]
                opAValue = self.NextState.PhysicalRegisterFile[instruction.opA] if opAReady else 0

                # Rename the registers
                oldDest = self.NextState.RegisterMapTable[instruction.dest]
                dest = self.NextState.FreeList.pop(0)
                # Update the register map table and busy bit table
                self.NextState.RegisterMapTable[instruction.dest] = dest
                self.NextState.BusyBitTable[dest] = True

                # Create an entry in the IntegerQueue
                self.NextState.IntegerQueue.append(IntegerQueueEntry(dest, opAReady, opA, opAValue, opBReady, opB, opBValue, opCode, decodedPC))
                # Create an entry in the ActiveList
                self.NextState.ActiveList.append(ActiveListEntry(False, False, instruction.dest, oldDest, decodedPC))
                
        else:
            self.NextState.Backpressure = True
    
    # Propagate the issue stage
    # Check if the operands are ready and issue the instruction
    # If the IntegerQueue is not empty, issue the first 4 instructions that are ready
    # If the IntegerQueue is empty, return
    def propagateIssue(self):
        if self.Exception or len(self.IntegerQueue) <= 0:
            return

        # Update forwarding paths
        for i in range(len(self.IntegerQueue)):
            if self.IntegerQueue[i].OpAIsReady != 1:
                self.IntegerQueue[i].OpAIsReady = not self.BusyBitTable[self.IntegerQueue[i].OpARegTag]
                self.IntegerQueue[i].OpAValue = self.PhysicalRegisterFile[self.IntegerQueue[i].OpARegTag] if self.IntegerQueue[i].OpAIsReady else self.IntegerQueue[i].OpAValue
            # No opB update for addi since it is an immediate value
            if self.IntegerQueue[i].OpBIsReady != 1:
                self.IntegerQueue[i].OpBIsReady = not self.BusyBitTable[self.IntegerQueue[i].OpBRegTag] 
                self.IntegerQueue[i].OpBValue = self.PhysicalRegisterFile[self.IntegerQueue[i].OpBRegTag] if self.IntegerQueue[i].OpBIsReady else self.IntegerQueue[i].OpBValue

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
   
    # Propagate the ALUs
    def propagateALUs(self):
        self.execute2()
        self.execute1()
    
    # Propagate the commit stage
    def propagateCommit(self):
        if self.Exception:
            if len(self.ActiveList) == 0: # Exception has been handled
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
                    logical = self.RegisterMapTable[entry.LogicalDestination]
                    if logical not in self.NextState.FreeList:
                        self.NextState.FreeList.append(logical)
                    if entry.OldDestination not in self.NextState.FreeList:
                        self.NextState.FreeList.append(entry.OldDestination)
                    self.NextState.BusyBitTable[logical] = False
                    self.NextState.BusyBitTable[entry.OldDestination] = False
                    self.NextState.RegisterMapTable[entry.LogicalDestination] = entry.OldDestination
                    
        # Skip if there are no active instructions
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
            entry = self.ActiveList[i-count]
            self.NextState.ActiveList.pop(i - count)
            self.ActiveList.pop(i - count) 
            self.NextState.FreeList.append(entry.OldDestination)
            
            # To be sure
            self.NextState.BusyBitTable[entry.OldDestination] = False 

    # Propagate the processor state
    def propagate(self):
        # Propagate each module
        self.propagateCommit()
        self.propagateALUs()
        self.propagateIssue()
        self.propagateRenameAndDispatch()
        self.propagateFetchAndDecode()
    
    # Latch the next state
    def latch(self):
        # Update the current state
        save = self.NextState
        self.__dict__.update(copy.deepcopy(self.NextState).__dict__)
        self.NextState = save

    # Save the log to the output file
    def saveLog(self, output_file):
        with open(output_file, "a") as f:
            json.dump(self.NextState.Log, f, indent=4, cls=MyEncoder, sort_keys=True)
    
    # Check if there are no more instructions to fetch and decode
    def noInstruction(self):
        return self.PC >= len(self.Instructions)

# Parse the instructions from the input file
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
    
    return parsed_instructions

# Main function
def main():

    if len(sys.argv) != 3:
        print("Usage: python3 main.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    

    #0. parse JSON to get the program
    instructions = parseInstructions(input_file);
    next_state = ProcessorState(None, instructions)
    current_state = ProcessorState(next_state, instructions)
    #1. dump the state of the reset system
    current_state.dumpStateIntoLog()
    #2. the loop for cycle-by-cycle iterations.
    i = 0
    while(not (current_state.noInstruction() and current_state.activeListIsEmpty()) and i < 50):
        #do propagation
        current_state.propagate();
        #advance clock, start next cycle
        current_state.latch();
        #dump the state
        i += 1
        current_state.dumpStateIntoLog()
    #3. save the output JSON log
    current_state.saveLog(output_file);
    

if __name__ == "__main__":
    main()


