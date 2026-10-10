"""Exercise the patched Mesa translation loop and draw cleanup with ownership tracking."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'artifacts/graphics-batching/u_vbuf.c').read_text()
start = source.index('   /* Translate buffers. */', source.index('u_vbuf_translate_begin('))
end = source.index('   /* Setup new vertex elements. */', start)
translate = source[start:end]
start = source.index('      /* The driver now owns references')
end = source.index('\n   }', start)
cleanup = source[start:end]
start = source.index('out:\n', source.index('void u_vbuf_draw_vbo('))
end = source.index('\n}', start)
failure_cleanup = source[start:end].replace('out:\n', '')
start = source.index('u_vbuf_upload_buffers(')
counter = source[source.index('   unsigned rcount = ', start):].split('\n', 1)[0]
start = source.index('         if (releasebufs[rcount])', start)
end = source.index('         real_vb->buffer_offset -= offset;', start)
user_cleanup = source[start:end]
c = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define VB_NUM 3
#define VB_VERTEX 0
#define PIPE_MAX_ATTRIBS 32
#define PIPE_OK 0
#define PIPE_ERROR_OUT_OF_MEMORY 1
#define align(x,a) (((x)+(a)-1)/(a)*(a))
enum pipe_error { OK=0, FAILED=1 };
struct pipe_resource {unsigned refs;};
struct translate_key {unsigned nr_elements, output_stride;};
struct u_vbuf {struct {bool attrib_element_unaligned;} caps; unsigned fallback_vbs[3];};
static struct pipe_resource resources[10000], *current, *bound[3];
static unsigned created, live, fail_type=99;
static void pipe_resource_release(void *pipe, struct pipe_resource *r) {
 (void)pipe; if(r){assert(r->refs);if(!--r->refs)live--;}
}
static enum pipe_error u_vbuf_translate_buffers(struct u_vbuf *mgr,
 struct translate_key *key, void *info, void *draw, unsigned mask,
 unsigned type, int start, unsigned num, int min_index, bool unroll,
 struct pipe_resource **releasebuf) {
 (void)mgr;(void)key;(void)info;(void)draw;(void)mask;(void)start;
 (void)min_index;(void)unroll;
 /* A reused upload writes NULL; rollover transfers the old owner's reference. */
 *releasebuf=NULL;
 if(num || !current){
  *releasebuf=current;current=&resources[created++];current->refs=1;live++;
 }
 /* Keep the translated borrowed pointer until the later driver bind. */
 bound[type]=current;
 return type==fail_type ? FAILED : OK;
}
static bool translation(struct u_vbuf *mgr, unsigned *release_count,
 struct pipe_resource **releasebufs, unsigned types, bool rollover) {
 unsigned type; void *info=NULL,*draw=NULL;
 struct translate_key key[3]={{0}}; unsigned mask[3]={0},min_alignment[3]={1,1,1};
 int start[3]={0},min_index=0;unsigned num[3]={rollover,rollover,rollover};
 bool unroll_indices=false;
 for(unsigned i=0;i<types;i++){key[i].nr_elements=1;key[i].output_stride=4;}
''' + translate + r'''
 return true;
}
static void release_draw(void *pipe,unsigned release_count,struct pipe_resource **releasebufs){
''' + cleanup + r'''
 (void)release_count;
}
static void release_failure(void *pipe,unsigned release_count,struct pipe_resource **releasebufs){
''' + failure_cleanup + r'''
}
static int append_user(unsigned *release_count,struct pipe_resource **releasebufs,bool valid){
 struct {struct {struct pipe_resource *resource;} buffer;} vb={0},*real_vb=&vb;
''' + counter + r'''
 struct pipe_resource *retired=&resources[created++];retired->refs=1;live++;
 releasebufs[rcount]=retired;real_vb->buffer.resource=valid?current:NULL;
''' + user_cleanup + r'''
 return PIPE_OK;
}
int main(void){
 struct u_vbuf mgr={0};mgr.caps.attrib_element_unaligned=true;
 for(unsigned t=0;t<3;t++)mgr.fallback_vbs[t]=t;
 struct pipe_resource *queue[PIPE_MAX_ATTRIBS+VB_NUM],*driver[3]={0};unsigned count;
 for(unsigned d=0;d<1500;d++){
  count=0;assert(translation(&mgr,&count,queue,3,true));assert(count<=3);
  /* No retired owner is dropped before all borrowed buffers are bound. */
  for(unsigned t=0;t<3;t++){assert(bound[t]->refs);bound[t]->refs++;}
  for(unsigned t=0;t<3;t++){pipe_resource_release(NULL,driver[t]);driver[t]=bound[t];}
  release_draw(NULL,count,queue);assert(live<=3);
  /* No rollover must not erase a retired entry from an earlier type. */
  count=0;assert(translation(&mgr,&count,queue,2,true));assert(translation(&mgr,&count,queue,1,false));
  assert(count==2);release_draw(NULL,count,queue);
 }
 count=0;assert(translation(&mgr,&count,queue,3,true));assert(count==3);
 for(unsigned i=0;i<PIPE_MAX_ATTRIBS;i++)assert(append_user(&count,queue,true)==PIPE_OK);
 assert(count==PIPE_MAX_ATTRIBS+VB_NUM);release_draw(NULL,count,queue);
 count=0;assert(append_user(&count,queue,false)==PIPE_ERROR_OUT_OF_MEMORY);
 assert(count==1);release_failure(NULL,count,queue);
 count=0;fail_type=1;assert(!translation(&mgr,&count,queue,3,true));assert(count==2);
 release_failure(NULL,count,queue);
 for(unsigned t=0;t<3;t++)pipe_resource_release(NULL,driver[t]);
 pipe_resource_release(NULL,current);assert(live==0);
 puts("PASS: 1500 multi-draw uploads stay bounded; every translated type retains borrowed buffers through binding; reuse and error cleanup release all owners");
}
'''
with tempfile.TemporaryDirectory(prefix='prosperomc-upload-') as tmp:
    path = Path(tmp)
    (path / 'check.c').write_text(c)
    subprocess.run(['cc', '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(path / 'check.c'), '-o', str(path / 'check')], check=True)
    subprocess.run([str(path / 'check')], check=True)
