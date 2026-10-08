#define main probe_once
#include "../../probe.cpp"
#undef main
int main(int argc,char **argv) {
  if(argc!=3)return 64;
  for(int i=0;i<100;++i){int result=probe_once(argc,argv);if(result)return result;}
  return 0;
}
