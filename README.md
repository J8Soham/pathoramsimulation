Pending changes and questions:

what is the size of the stash? 
+ log(n) * number of blocks in a bucket + (80) (Proof: simple path oram implementation / max stash size 80)
- evict on path 2, so during the execution of read and write we don't know as it can exceed it. after eviction the number of blocks in the stash can exceed 80. it is not (number of leaf node) as it is insane for large tree size. 2*n-1 nodes. negligible probablity. 

what if we make the stash a queue or stack does it change leakage? ()
+ no it doesn't change the leakage. Stash is stored on the client so it can't ever have any leakage (only what the server can observe)

when done with read and write do we transvere every part of the stash?
+ it is an array you have to try and evict everything in the stast. 


when initializing do we push dumpy blocks everywhere?
+ yes, when need to intializie 
+ If we start with dummies and each block contains dummie. Write operation 

reminder: 
When eviction you need to use the potion map value to put it back in the correct place. 