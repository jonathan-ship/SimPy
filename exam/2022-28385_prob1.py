# availability = m_f/(m_f+m_r)
# A_1 = 48/(48+8) = 0.8571
# A_2 = 3.3/(3.3+1/6) = 0.9519

# te_1 = t_01/A_1 = 19 / 0.8571 = 22.17 [min]
# te_2 = t_02/A_2 = 22 / 0.9519 = 23.11 [min]

# u_1 = TH * te_1 = 2.4 * (22.17/60) = 0.8868
# u_2 = TH * te_2 = 2.4 * (23.11/60) = 0.9244

#Effective variability
# c_e**2 = (sigma_e**2/te**2) = c_0**2 +(1+c_r**2) * A * (1-A) * (m_r/t_0)

# c_e1**2 = 6.438
# c_e2**2 = 1.042


#Theoretical answer
# CT_q1 = 645.91 [min]
# WIP_q1 = 25.84
# CT_q2 = 892.8 [min]
# WIP_q2 = 35.71

# Theoretical answer와 값을 비교하기 위해 Simulation model 결과,
# 100,000,000번 이상 실행 시에는 Theoretical 값에 수렴 하는 것을 확인
# CT_q1 = 645.91 [min]
# WIP_q1 = 25.84
# CT_q2 = 892.8 [min]
# WIP_q2 = 35.71