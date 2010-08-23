#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef THREADS_T
#define THREADS_T

/**@defgroup Parallel Parallel Stuff
 * @{
 */

class ThreadManager;
class ThreadArgument;

/** Prototype of functions for threads works. */
typedef void (*ThreadFunction) (ThreadArgument &arg);

/** Class wrapping around the pthreads mutex.
 * This class will provide a more object oriented implementation
 * of a mutex, to ensure the unique access to critical regions of
 * code and other syncronization problems.
 */
class Mutex
{
private:
    pthread_mutex_t mutex; //our pthread mutex

public:
    /** Default constructor.
     * This constructor just initialize the pthread_mutex_t structure
     * with its defaults values, just like static initialization with PTHREAD_MUTEX_INITIALIZER
     */
    Mutex();

    /** Destructor. */
    ~Mutex();

    /** Function to get the access to the mutex.
     * If the some thread has the mutex and other
     * ask to lock will be waiting until the first one
     * release the mutex
     */
    void lock();

    /** Function to release the mutex.
     * This allow the access to the mutex to other
     * threads that are waiting for it.
     */
    void unlock();
}
;//end of class Mutex

/** Class to syncronize several threads in some point of execution.
 * Threads is a way of distributing workload across
 * different workers to solve a problem faster. Nevertheless, sometimes
 * we need synchronization between threads to avoid undesired race
 * conditions and other problems. Here we are an implementation of a barrier
 * that allows putting all threads to wait at a given point until all of them
 * have reached such point and can continue working. Barriers are usually
 * available through pthreads system library. Nonetheless, sometimes it is not
 * so we have to implement it here.
 * @code
 * Mutex mutex;
 *
 * //Then in each thread to access the critical section:
 *  mutex.lock();
 *  //...Do critical section stuff
 *  mutex.unlock();
 *
   @endcode
 */
class Barrier
{
private:
    int needed; ///< How many threads should arraive to meet point
    int called; ///< How many threads already arrived
    pthread_mutex_t mutex; ///< Mutex to update structure
    pthread_cond_t cond; ///< Condition on which the threads are waiting

public:
    /** Constructor of the barrier to initialize the object.
     * You should pass the number of working threads that
     * you want to wait on the barrier. The internal counter
     * of the barrier will be initialized with numberOfThreads + 1
     * taking into account the main thread, so it need to wait
     * also in the barrier with the worker threads to all
     * can move on.
     * @code
     *  //For syncronize 10 threads created by a main thread
     *  //you can create the barrier from the main thread
     *  Barrier * barrier = new Barrier(10);
     *  //...
     *  //In the syncronization point
     *  barrier->wait();
     * @endcode
     * */
    Barrier(int numberOfThreads);

    /** Destructor to free all memory used */
    ~Barrier();

    /** Request to wait in this meet point.
     * For each thread calling this function the execution will
     * be paused untill all threads arrive this point.
     */
    void wait();

}
;//end of class Barrier

/** Class to pass arguments to threads functions.
 * The argument passed can be obtained casting
 * the void * data received in the function.
 * @see ThreadManager
 */
class ThreadArgument
{
private:
    ThreadManager * manager;
public:
    int thread_id; ///< The thread id
    void * workClass; ///< The class in wich threads will be working
    void * data;

    ThreadArgument();
    ThreadArgument(int id, ThreadManager * manager = NULL, void * data = NULL);

    friend class ThreadManager;
    friend void * _threadMain(void * data);
};

void * _threadMain(void * data);

/** Class for manage a group of threads performing one or several tasks.
 * This class is very useful when we have some function that can be executed
 * in parrallel by threads. The threads are created in the contructor of the object
 * and released in destructor. This way threads can execute different
 * functions at diffent moments and exit at the end of manager life. Also, the
 * wait() function allow in the main thread to wait until all threads have
 * finish working on a task and maybe then execute another one.
 * This class is supposed to be used only in the main thread.
 */
class ThreadManager
{
private:
    int threads; ///< number of working threads.
    pthread_t * ids; ///< pthreads identifiers
    ThreadArgument * arguments; ///< Arguments passed to threads
    Barrier * barrier; ///< barrier for syncronized between tasks.
    /// Pointer to the function to work on,
    /// if null threads should exit
    ThreadFunction workFunction;

public:
    /** Constructor, number of working threads should be supplied */
    ThreadManager(int numberOfThreads, void * workClass = NULL);

    /** Destructor, free memory and exit threads */
    ~ThreadManager();

    /** Function to start working in a task.
     * The function that want to be executed in parallel
     * by the working threads should be passed as argument.
     * Functions that can be executed by thread should by of the
     * type ThreadFunction, i.e., return void * and only
     * one argument of type ThreadArgument.
     * The call of this function will block the main thread
     * until all workers finish their job, if you dont want to block
     * use runAsync instead, and later can call wait for waiting
     * until threads are done.
     * @code
     *
     *  //Global variables, so it are visible in 'processSeveralImages()'
     *  ParallelTaskDistributor * td;
     *  //function to perform some operation
     *  //to N images executed in parellel
     *  void * processImages(ThreadArgument & data)
     *  {
     *      int thread_id = arg.thread_id;
     *
     *      long long int firstImage, lastImage;
     *      while (td->getTasks(firstImage, lastImage))
     *          for (int image = firstImage; image <= lastImage; ++image)
     *          {
     *              //...
     *              processOneImage(image);
     *              //...
     *          }
     *  }
     *
     *  int main()
     *  {
     *  //...
     *  //Distribute 1000 tasks in blocks of 100.
     *  td = new ThreadTaskDistributor(1000, 100);
     *  //Start 2 threads to work on it
     *  ThreadManager * tm = new ThreadManager(2);
     *  tm.run(processImages);
     *  //...
     *  //Same threads can work in other function
     *  tm.run(processVolumes);
     *  }
     * @endcode
     */
    void run(ThreadFunction function);

    /** Same as run but without blocking. */
    void runAsync(ThreadFunction function);

    /** Function that should be called to wait until all threads finished work */
    void wait();

    /** function to start running the threads.
     * Should be external and declared as friend */
    friend void * _threadMain(void * data);


}
;//end of class ThreadManager

/** Just a type definition for shortcut 'long long int' */
typedef long long int longint;

/** This class distributes dynamically N tasks between parallel workers.
 * @ingroup ParallelLibrary
 * This class is a generalization of a common task in a parallel
 * environment of dynamically distribute N tasks between workers(threads or mpi proccess).
 * Each worker will ask for a group of tasks, proccess it and ask for more tasks
 * until there is not more task to process.
 *
 * This class is abstract and only serves as base for
 * concrete implementations, which will provides the
 * specific lock mechanisms and the way of distribution.
 */
class ParallelTaskDistributor
{
protected:
    //The total number of tasks to be distributed
    longint numberOfTasks;
    //How many tasks give in each request
    longint blockSize;
    //The number of tasks that have been assigned
    longint assignedTasks;

public:
    /** Constructor.
     * The number of jobs and block size should be provided.
     */
    /** Constructor for Master node.
     */
    ParallelTaskDistributor(longint nTasks, longint bSize);

    /** Destructor.
     */
    virtual ~ParallelTaskDistributor()
    {}
    ;

    /** Restart the number of assigned tasks and distribution again.
     * This method should only be called in the main thread
     * before start distributing the tasks between the workers
     * threads.
     */
    void clear();

    /** Set the number of tasks assigned in each request */
    void setBlockSize(longint bSize);

    /** Return the number of tasks assigned in each request */
    int getBlockSize() const;

    /** Gets parallel tasks.
     *  @ingroup ParallelJobHandler
     *  This function will be called by workers for asking tasks
     *  until there are not more tasks to process.
     *  Example:
     *  @code
     *  //...
     *  ParallelTaskDistributor * td = new ThreadTaskDistributor(1000, 100);
     *  //...
     *  //function to perform some operation
     *  //to N images executed in parellel
     *  void processSeveralImages()
     *  {
     *      longint firstImage, lastImage;
     *      while (td->getTasks(firstImage, lastImage))
     *          for (longint image = firstImage; image <= lastImage; ++image)
     *          {
     *              //...
     *              processOneImage(image);
     *              //...
     *          }
     *  }
     *  @endcode
     */
    bool getTasks(longint &first, longint &last); // False = no more jobs, true = more jobs


protected:
    //Virtual functions that should be implemented in
    //subclasses, providing a mechanism of lock and
    //the specific way of distribute tasks.
    virtual void lock() = 0;
    virtual void unlock() = 0;
    virtual bool distribute(longint &first, longint &last) = 0;

}
;//class ParallelTaskDistributor

/** This class is a concrete implementation of ParallelTaskDistributor for POSIX threads.
 * It use mutex as the locking mechanism
 * and distributes tasks from 0 to numberOfTasks.
 */
class ThreadTaskDistributor: public ParallelTaskDistributor
{
public:
    ThreadTaskDistributor(longint nTasks, longint bSize):ParallelTaskDistributor(nTasks, bSize)
    {}
    virtual ~ThreadTaskDistributor(){};
protected:
    Mutex mutex; ///< Mutex to syncronize access to critical region
    virtual void lock();
    virtual void unlock();
    virtual bool distribute(longint &first, longint &last);
};//end of class ThreadTaskDistributor

/** @name Old parallel stuff. */
/** Barrier structure */
typedef struct mybarrier_t {
	/// How many threads should be awaited
    int needed;
    /// How many threads already arrived
    int called;
    /// Mutex to update this structure
    pthread_mutex_t mutex;
    /// Condition on which the threads are waiting
    pthread_cond_t cond;
} barrier_t;

/** Barrier initialization */
int barrier_init(barrier_t *barrier, int needed);
/** Barrier destruction */
int barrier_destroy(barrier_t *barrier);
/** Wait at the barrier */
int barrier_wait(barrier_t *barrier);
/** @} */

#endif
