// Bounded instruction harness for the observed CH PS3 revision.
// Run on a decoded analysis copy in Ghidra. Synthetic callback objects only;
// neither the game nor RPCS3 runs, and no executable is written or patched.
// Argument: output JSON path, chosen separately from all source files.
import ghidra.app.script.GhidraScript;
import ghidra.app.emulator.EmulatorHelper;
import java.nio.file.*;
import java.util.*;
public class AllocatorABITrace extends GhidraScript {
 private void verifyEntry(long descriptor,long entry) throws Exception {
  if(getInt(toAddr(descriptor))!=(int)entry || getInt(toAddr(descriptor+4))!=0xa64a94)
   throw new Exception("Unsupported allocator descriptor revision");
 }
 private void verifyRevision() throws Exception {
  if(getInt(toAddr(0x12773af8L))!=0xa4a758 || getInt(toAddr(0x12773afcL))!=0xa4a760
     ||getInt(toAddr(0x843404L))!=0xf821ff91||getInt(toAddr(0x8434b8L))!=0xf821ff91)
   throw new Exception("Unsupported allocator wrapper revision");
  verifyEntry(0xa4a758L,0x843404L);verifyEntry(0xa4a760L,0x8434b8L);
  long allocateDescriptor=Integer.toUnsignedLong(getInt(toAddr(0x127735ccL)));
  long freeDescriptor=Integer.toUnsignedLong(getInt(toAddr(0x12773588L)));
  verifyEntry(allocateDescriptor,0x8258c0L);verifyEntry(freeDescriptor,0x8248a8L);
 }
 private void word(EmulatorHelper e,long a,long value){e.writeMemoryValue(toAddr(a),4,value);}
 private String runCase(boolean free,int flag,long returned) throws Exception {
  EmulatorHelper e=new EmulatorHelper(currentProgram);
  try {
   long object=0x40002000L,heap=0x40004000L,vt=0x40003000L,descriptor=0x40005000L,callee=0x40006000L,done=0x40007000L;
   e.writeMemory(toAddr(0x40000000L),new byte[0x8000]);
   word(e,object+0x10,flag);word(e,object+0x14,heap);word(e,heap,vt);word(e,heap+0x18,7);
   word(e,vt+(free?8:0x4c),descriptor);word(e,descriptor,callee);word(e,descriptor+4,0x55667788L);
   e.writeRegister("xer_so",0);e.writeRegister("r1",0x40001000L);e.writeRegister("r2",0xa64a94L);e.writeRegister("r3",object);
   e.writeRegister("r4",free?0x20001000L:4096);e.writeRegister("r5",128);e.writeRegister("r6",0x1234);e.writeRegister("r7",0x5678);
   e.writeRegister("LR",done);e.writeRegister(e.getPCRegister(),free?0x8434b8L:0x843404L);
   boolean trapped=false;List<Long> args=new ArrayList<>();long toc=0;
   for(int step=0;step<128;step++){
    long pc=e.getExecutionAddress().getOffset();
    if(pc==done){
     if(!trapped)throw new Exception("Did not reach synthetic heap callback");
     long result=e.readRegister("r3").longValue(),restored=e.readRegister("r2").longValue();
     List<Long> expected=free?Arrays.asList(heap,0x20001000L,0L,0L):Arrays.asList(heap,4096L,128L,flag==0?7L:3L,0x1234L,0x5678L);
     if(!args.equals(expected)||toc!=0x55667788L||restored!=0xa64a94L||result!=(free?1L:returned))throw new Exception("ABI mismatch: "+args+" result="+result);
     return "{\"free\":"+free+",\"flag\":"+flag+",\"callback_arguments\":"+args+",\"callback_toc\":"+toc+",\"restored_toc\":"+restored+",\"result\":"+result+",\"passed\":true}";
    }
    if(pc==callee){
     trapped=true;toc=e.readRegister("r2").longValue();for(int n=3;n<=(free?6:8);n++)args.add(e.readRegister("r"+n).longValue());
     e.writeRegister("r3",returned);e.writeRegister(e.getPCRegister(),e.readRegister("LR"));continue;
    }
    if(!e.step(monitor))throw new Exception("Instruction step failed at "+Long.toHexString(pc)+": "+e.getLastError());
   }
   throw new Exception("Instruction bound exceeded");
  }finally{e.dispose();}
 }
 public void run() throws Exception {
  verifyRevision();
  Path output=Paths.get(getScriptArgs()[0]).toAbsolutePath().normalize();
  String executableName=currentProgram.getExecutablePath();
  if(System.getProperty("os.name").startsWith("Windows")&&executableName.matches("^/[A-Za-z]:.*"))executableName=executableName.substring(1);
  Path executable=Paths.get(executableName).toAbsolutePath().normalize();
  if(output.equals(executable)||Files.exists(output))throw new Exception("Choose a new output JSON; sources/existing reports remain immutable");
  List<String> rows=new ArrayList<>();rows.add(runCase(false,0,0x20001000L));rows.add(runCase(false,1,0x20001000L));rows.add(runCase(false,0,0));rows.add(runCase(true,0,0));
  Files.writeString(output,"[\n"+String.join(",\n",rows)+"\n]\n",StandardOpenOption.CREATE_NEW);println("Allocator ABI native instruction cases: "+rows.size()+" passed");
 }
}
