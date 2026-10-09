// Copyright 2026 Technologies Kesis & Sisters Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#define main probe_once
#include "../../probe.cpp"
#undef main
int main(int argc,char **argv) {
  if(argc!=3)return 64;
  for(int i=0;i<100;++i){int result=probe_once(argc,argv);if(result)return result;}
  return 0;
}
