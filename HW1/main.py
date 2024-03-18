import json
import sys
import copy

# TODO Exception done by Commit
# TODO ExceptionPC = PC of the instruction that caused the exception

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
    
class ActiveListEntry:
    def __init__(self, Done, Exception, LogicalDestination, OldDestination, PC):
        self.Done = Done
        self.Exception = Exception
        self.LogicalDestination = LogicalDestination
        self.OldDestination = OldDestination
        self.PC = PC

class ProcessorState:
    def __init__(self, NextState, Instructions):
        # Initialize data structures
        self.Cycle = 0
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

    def dumpStateIntoLog(self):
        # Create dictionary to represent state
        state_dict = {
            "Cycle": self.Cycle,
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
        }   
        self.Log.append(state_dict)
        # Output state to JSON file
        print(self.Log)
        with open(f"cycle_{self.Cycle}.json", "w") as f:
            json.dump(state_dict, f, indent=4)
    

    def activeListIsEmpty(self):
        return len(self.ActiveList) == 0
    
    def propagateFetchAndDecode(self):
        count = 1
        # Fetch and decode the next instruction
        if self.Exception: # TODO is Commit stage setting PC to 0x10000 or is it here (then we check self.Exception)
            #self.NextState.PC = self.ExceptionPC
            #self.NextState.PC = 0x10000
            # TODO FLLUSH DIR etc
        if self.Backpressure:
            return 
        while(self.PC + count < len(self.Instructions) and count < 5):
            self.NextState.DecodedPCs.append(self.PC + count - 1)
            self.NextState.PC += 1
            count += 1
            print("count: ", count-1)
    
    def propagateRenameAndDispatch(self):
        # TODO if there is space in the IntegerQueue and ActiveList and FreeList (size of the DIR, if 3 instructions only, then 3 in each list minimum)
        if len(self.FreeList) > 3 and len(self.IntegerQueue) < 29 and len(self.ActiveList) < 29:
            if len(self.DecodedPCs) > 0:
            # TODO Rename the registers
            # TODO Dispatch the instruction to the ActiveList and IntegerQueue
            # Observe the results of all functional units through the forwarding paths and update the physical register file as well as the Busy Bit Table
                pass
        else:
            self.NextState.Backpressure = True
    
    def propagateIssue(self):
        # TODO if there is space in the ALUs
        if len(self.ActiveList) > 0:
            # TODO Issue the instruction to the ALUs
            pass
    
    def propagateALUs(self):
        # TODO if there is an instruction in the ALUs
        # TODO Execute the instruction
        pass

    def propagateCommit(self):
        # TODO if there is an instruction in the Commit stage
        # TODO Commit the instruction
        pass

    def propagate(self):
        # Propagate each module
        self.propagateCommit()
        self.propagateALUs()
        self.propagateIssue()
        self.propagateRenameAndDispatch()
        self.propagateFetchAndDecode()
    
    def latch(self):
        # Advance clock
        self.NextState.Cycle += 1
        # Latch the next state
        save = self.NextState
        self.__dict__.update(copy.deepcopy(self.NextState).__dict__)
        self.NextState = save


    def saveLog(self, output_file):
        print(self.Log)
        with open(output_file, "a") as f:
            json.dump(self.Log, f, indent=4)
    
    def noInstruction(self):
        print("PC: ", self.PC, " len(instructions): ", len(self.Instructions))
        return self.PC >= len(self.Instructions)

def parseInstructions(filepath):
    parsed_instructions = []
    with open(filepath, "r") as file:
        instruction_json = json.load(file)
        for instruction_str in instruction_json:
            instruction_parts = instruction_str.split()
            mnemonic = instruction_parts[0]
            dest = instruction_parts[1][:-1]  # Remove the comma
            opA = instruction_parts[2][:-1]  # Remove the comma
            opB = instruction_parts[3]
            if mnemonic == "addi":
                imm = int(instruction_parts[3])
                parsed_instructions.append({"mnemonic": mnemonic, "dest": dest, "opA": opA, "imm": imm})
            else:
                parsed_instructions.append({"mnemonic": mnemonic, "dest": dest, "opA": opA, "opB": opB})
    
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
    current_state.dumpStateIntoLog();
    #2. the loop for cycle-by-cycle iterations.
    i= 0
    while(not (current_state.noInstruction() and current_state.activeListIsEmpty())and i < 10):
        #do propagation
        #if you have multiple modules, propagate each of them
        current_state.propagate();
        #advance clock, start next cycle
        current_state.latch();
        #dump the state
        current_state.dumpStateIntoLog()
        i += 1
    #3. save the output JSON log
    current_state.saveLog(output_file);
    

if __name__ == "__main__":
    main()


