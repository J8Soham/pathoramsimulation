# How much do different leakages actually help an adversary?”

Hi there you reached my experimentations for leakages in my CSE 108C research oriented class. Basically the goal of the project was to read reseearch papers, ask questions, and mess around with code so we can get into the nitty details of our work and then possibly come up with our own ideas. 

Here is a summary of what I did:

Algorithms implementd:

SEAL - This is a wrapper on top of our Path-ORAM implementation implented in seal_client.py

Path-ORAM (client.py): Currently using a position map version of Path-ORAM. We could go many different ways like use AVL trees (Oblix or Oblivious Data Structures paper) or resurssive. I didn't because this is just a simulation and efficiency is not the main goal here.

# Design decisions:
1. I figured that we don't need to do anything with actually sending our info like with serves and stuff we could just have classes that represent the server and client. 
2. In construction of ADJ-ORAM what I did was that I would initialize all of my ORAMs this would fill it completely with dummy blocks then for each element needing to be entered do a write for that ORAM (based on a function called prp to oram). I realize that in the ADJ-ORAM Initialize we just create 2^a arrays that are populated with the values and then intialized them but I can't see how mine would affect leakage.
3. One of the things I really wanted was for this to be modular and that each of the stuff I have be 

# Files (where is everything implemented)
### main.py: 
First attack: Query Recovery Attack 
Basically the adversary needs to find which keyword was queried
1. knows the plaintext dataset  
2. knows the queries t_q and resulting volumes
Now the goal is to match the queries t_q to which keyword from the dataset by using the matching volumes (hypothetically padding will reduce this as it has to choose from more keywords with similar volumes)

Second Attack: Database Recovery Attack 
Basically the adversary needs to find which keyword was queried
1. knows the plaintext dataset 
2. knows the queries t_q and resulting encrypted tuples as well as which ORAM that querry went to (alpha bit)
now the goal with the encrypted dataset can it match the encrypted tuples for a query can it match what plaintext tuple was given to get the keyword. 

test_path_oram() - Tests if the Path ORAM created works.
test_seal() - Tests if the SEAL on top of Path-ORAM workss.
test_simulation() - The first version of the test I did to for the tcp-h and chicago dataset how the query recovery and database recovery attacks are working out. Created the seal_vs_pathoram png. 

I got very weird results the first time when I was using the simulation for seal so I figured to create test_simulation_equivalence

test_simulation_equivalence() - Basically was like a sanity check to see if the simulation of SEAL and actual SEAL gave me same results. Be warned this attack if you wanna recreate the 10000 one takes like 1-2 hours (at least on my MAC.) What I could have done is that because I study at Kresge split the datasets and then run it on two different machines. But I didn't know the first time. 

Then I ran the with the new simulation test and it worked. I also changed the plots and they are the attribute5 (database and querry) that look prettier. 

test_simulation_second_gen(): After this proof that the main code may work (there were a few errors after like with qurry attack the poping made it weird for the plots (even though the psuedocode in SEAL does so - I guess they meant check for the element or I missed something)). I did recreate most of the paper + a few more fun things like the convergence. I also was wondering if uneven or values of x not to the power of 2 would affect querry attacks for my values they didn't (I think a useful thing would be to try for more values and database recover attack). 

### client.py: 
Basically my implementation of Path-ORAM (position map version) 

### client_seal.py
Basically my implementation of SEAL on top of Path-ORAM 

### clien_simulator.py:
This was interesting basically what you can do is that because actually using SEAL is very expensive. We can just focus on what we need for the attacks to work. There are bunch of functions there that basically help you with doing so defined there. The main idea is that you don't need to actually intialize the Path-ORAM and then do the operations as you can just track which ORAM would have been accessed. 

### load_data.py
specific for loading the datasets mentioned above. (i.e. chicago crimes, tpch, apartments). There is the duplicated of crimes and apartments because the first functions only get one attributes. I was smarter when creating tpch do just get all (same access time) and just filter for the one I want. I also have the crime join querry for supplier and nation just like the one in SEAL (just to check out DR success being low in SEAL as compared to Path-ORAM which is one of the interesting results of the paper for me). 

# How to run:
If you have come this far thanks. 

Basically the first things you might need to do is download datasets I used the ones in SEAL i.e. the Chicago Crimes and the TCP-H (https://www.usenix.org/system/files/sec20-demertzis.pdf) scroll to the very end for the links. 
In TCP-H you need to run make as well as a -gen command with scaling factor as 0.1 
I also used an Apartments dataset from Kaggle (https://www.kaggle.com/datasets/thedevastator5/apartments-for-rent-classified-10k-listings) for 10k to make my covergence plot as well as like a dr test I wanted to do. 

Then I think just create a venv environment and download the requirements. 

Then you are done with setup in the very end of the main file I have different tests that you can uncomment and see the results of! 

# Questions I had: 

what is the size of the stash? 
+ log(n) * number of blocks in a bucket + (80) (Proof: simple path oram implementation / max stash size 80)
- evict on path 2, so during the execution of read and write we don't know as it can exceed it. after eviction the number of blocks in the stash can exceed 80. it is not (number of leaf node) as it is insane for large tree size. 2*n-1 nodes. negligible probablity. 

what if we make the stash a queue or stack does it change leakage? ()
+ no it doesn't change the leakage. Stash is stored on the client so it can't ever have any leakage (only what the server can observe)

when done with read and write do we transvere every part of the stash?
+ it is an array you have to try and evict everything in the stast. 

when initializing do we push dumpy blocks everywhere?
+ yes, when need to intializie and done on the client side.  
+ If we start with dummies and each block contains dummie. Write operation 

reminder: 
When eviction you need to use the potion map value to put it back in the correct place. 

we don't have to prove that the path-oram is oblivious.

Thank you Apostolos again for answering them with patience :)


# Fun things next: 
+ get the side channels attack working
+ try the naive approach to make SEAL dynamic
+ clean up the code (i.e. get the test_simulation_equivalence plotting outside)

