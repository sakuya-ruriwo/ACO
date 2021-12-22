import init
import numpy as np
import random
import bisect
import math

Q = 1000

def runACO(benchmark_file_path , try_num , a , b , g , qzero , r) :
    global alpha , beta ,gamma ,q0 , rho

    alpha = a
    beta = b
    gamma = g
    q0 = qzero
    rho = r

    capacity , dimension , customer_location_list , node_demand , service_time , time_window , dist_list = init.init(benchmark_file_path)

    eta = calc_eta(dist_list)
    vnodes = []
    
    tau = np.ones((dimension + 1 , dimension + 1))
    vehicle_routes = []
    min_cost = 9999
    
    for i in range(0 , try_num):
        vnodes = []
        cvehicle_routes = []
        vehicle_num = 0
        sum_cost = 0

        while len(vnodes) != dimension - 1:
            candi_route = route_search(eta , tau , capacity , vnodes , dimension , node_demand , dist_list , time_window , service_time)
            
            if candi_route == 0:
                vnodes = []
                cvehicle_routes = []
                vehicle_num = 0
                sum_cost = 0
                continue

            cvehicle_routes.append(candi_route)
            vehicle_num += 1
            sum_cost += calc_cost(candi_route , dist_list)
            vnodes.extend(candi_route)
        
        if sum_cost < min_cost:
            vehicle_routes = cvehicle_routes
            min_cost = sum_cost
            rvehicle_num = vehicle_num
        
        route_value = Q / (sum_cost * vehicle_num)#使用台数が多いルートはフェロモンの量少なく
        #route_value = Q / sum_cost
        for j in vehicle_routes:
            tau = trail_update(tau , j , route_value)

    
    para = {"Alpha" : alpha , "Beta" : beta , "Gamma" : gamma , "q0" : q0 , "Rho" : rho}
                
    return vehicle_routes , sum_cost , rvehicle_num , customer_location_list , para

def calc_eta(Dist_list):
    const = 1
    eta = Dist_list / const
    eta[eta == 0] = np.inf
    eta = eta ** -1
    return eta
 

def route_search(Eta , Tau , Capacity , Vnodes , Dimension , Node_demand , Dist_list , Time_window , Service_time):
    candi_nodes = list(range(2,Dimension + 1))
    for i in Vnodes:#訪問先候補の決定訪問済み除外
        try:
            candi_nodes.remove(i)
        except:
            pass

    curfew = Time_window[1][1]#門限
    pcandi_nodes = candi_nodes
    

    while True:
        if len(pcandi_nodes) == 0:
            return 0 
        first_node_prob = calc_prob(1 , pcandi_nodes ,Eta , Tau , Time_window)#デポから進む各ノードの確率
        first_node = dec_nextnode(pcandi_nodes , first_node_prob)#デポから進むノードの決定
        if  Time_window[first_node][0] < Dist_list[1][first_node] and Dist_list[1][first_node] < Time_window[first_node][1]:
            time = Dist_list[1][first_node] + Service_time[first_node]
            break 
        elif  Dist_list[1][first_node] < Time_window[first_node][0] : # and Time_window[first_node][0] < curfew * 0.5:
            time = Time_window[first_node][0] + Service_time[first_node]
            break
        pcandi_nodes.remove(first_node)
    
    """psum = 0
    dsum = 0
    for i in candi_nodes:
        psum += Tau[1][i]
        dsum += Eta[1][i]
    print(Tau[1][first_node] / psum , Eta[1][first_node] / dsum  , "\n")"""


    route = [first_node]
    cap = Node_demand[first_node]
    curr_node = first_node
    candi_nodes.remove(curr_node)
    pcandi_nodes = candi_nodes


    while len(pcandi_nodes) > 0:#訪問先なくなったらデポへ
        pcandi_nodes_prob = calc_prob(curr_node ,pcandi_nodes , Eta , Tau , Time_window)
        nextnode = dec_nextnode(pcandi_nodes , pcandi_nodes_prob)
        new_time = time + Dist_list[curr_node][nextnode]
        if  Time_window[nextnode][1] > new_time:
            pcandi_nodes.remove(nextnode)
            continue
        elif new_time < Time_window[nextnode][0]:
            new_time = Time_window[nextnode][0]

        route.append(nextnode)
        curr_node = nextnode
        candi_nodes.remove(curr_node)
        pcandi_nodes = candi_nodes


        cap += Node_demand[nextnode]

        if cap > Capacity:#車両の容量超えたらルートから外して終了
            route.pop()
            break

        time = new_time + Service_time[nextnode]
        if (time + Dist_list[curr_node][1]) > curfew:#総時間がデポの期限を超えたらルートから外して終了
            route.pop()
            break

    return route


def calc_prob(Curr_node , Candi_nodes , Eta , Tau , Time_window):#現在のノード（Curr_node）から進むことが可能な候補ノード（Candi_nodes）の各確率
    pheromone_list = []
    for i in Candi_nodes:
        if Tau[Curr_node][i] == 0:
            pheromone_list.append(0)
        else:
            width = (Time_window[i][1] - Time_window[i][0]) ** -1
            pheromone_list.append((Tau[Curr_node][i] ** alpha) * (Eta[Curr_node][i] ** beta) * (width ** gamma))
    phero_sum = sum(pheromone_list)
    
    if phero_sum == 0:
        prob_list = pheromone_list
    else:
        prob_list = pheromone_list / phero_sum
    
    csumprob_list = [prob_list[0]]
    for i in range(1 , len(prob_list)):
        csumprob_list.append(csumprob_list[-1] + prob_list[i])

    return csumprob_list


def dec_nextnode(Candi_nodes , Candi_nodes_prob):#確率に基づいて進むノードを決定する
    q = random.uniform(0.0 , 0.999999999)
    if q <= q0:
        return Candi_nodes[Candi_nodes_prob.index(max(Candi_nodes_prob))]

    random_p = random.uniform(0.0 , 0.999999999)
    ni = bisect.bisect_left(Candi_nodes_prob , random_p)
    if ni >= len(Candi_nodes):
        return Candi_nodes[random.randint(0 , len(Candi_nodes) - 1)]
    
    return Candi_nodes[ni]


def trail_update(Tau , Ants_route , add_phero ):
    Tau = Tau * rho

    Tau[1][Ants_route[0]] += add_phero
    Tau[Ants_route[0]][1] += add_phero
    Tau[Ants_route[-1]][1] += add_phero
    Tau[1][Ants_route[-1]] += add_phero

    for i in range(0,len(Ants_route) - 1):
        nphero = Tau[Ants_route[i]][Ants_route[i+1]] + add_phero
        Tau[Ants_route[i]][Ants_route[i+1]] = nphero
        Tau[Ants_route[i+1]][Ants_route[i]] = nphero
    return Tau 


def calc_cost(Ant_route , Edge_cost_list):
    csum = Edge_cost_list[1][Ant_route[0]] + Edge_cost_list[Ant_route[-1]][1]
    for i in range(0,len(Ant_route) - 1):
        csum += Edge_cost_list[Ant_route[i]][Ant_route[i+1]]

    return int(csum)
