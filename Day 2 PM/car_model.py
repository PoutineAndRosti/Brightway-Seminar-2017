import xlrd
import numpy as np

RHO_AIR = 1.2  # air density for aerodynamic calculations

def get_driving_cycles():
    wb = xlrd.open_workbook("data/Automated car driving cycles.xlsx")
    ws = wb.sheet_by_name("Sheet1")
    headers = [ws.cell(0, x).value for x in range(1, ws.ncols)]
    return {header: np.array([float(ws.cell(row, index + 1).value)
                              for row in range(1, ws.nrows)
                              if ws.cell(row, index + 1).value != ''])
            for index, header in enumerate(headers)}

cycle = get_driving_cycles()['WLTP']


def energy_consumption(mass, efficiency, surface_area, aux_power,
                       motor_power, max_recup, min_recup_speed, Cr, Cd,
                       geno_eff):
    # Unit conversion km/h to m/s
    velocity = cycle / 3.6

    acceleration = np.zeros(cycle.shape)
    acceleration[1:-1] = (velocity[2:] - velocity[:-2]) / 2

    kinetic_force = acceleration * mass
    rolling_resistance = np.ones(cycle.shape) * mass * Cr * 9.81
    air_resistance = (velocity ** 2 * surface_area * Cd * RHO_AIR / 2)

    # Total force required at the wheel to meet acceleration requirement. rolling and
    # air resistance are always positive (resisting motion) but kinetic force
    # can be negative, when the car is decelerating.
    total_force = kinetic_force + rolling_resistance + air_resistance
    power = total_force * velocity
    idling = (velocity == 0) * 1

    arrays = np.recarray(
        velocity.shape,
        dtype=[(col, float) for col in 'kraw']
    )

    arrays.k = kinetic_force * velocity
    arrays.r = rolling_resistance * velocity
    arrays.a = air_resistance * velocity
    arrays.w = power  # arrays.k + arrays.r + arrays.a

    decelerating = total_force < 0

    pa = arrays.copy()
    # Set all four columns to all zeros when `decelerating` mask array is True
    pa[decelerating] = (0,0,0,0)

    pd = arrays.copy()
    pd[~decelerating] = (0,0,0,0)
    recuperating = -1 * pd.w < (max_recup * motor_power * 1000)
    recup_speed_limit = cycle > min_recup_speed
    recuperated_power = recuperating * recup_speed_limit * geno_eff * pd.w
    braking_power = ~(recuperating * recup_speed_limit) * pd.w

    # Convert to km; velocity is m/s, times 1 second
    distance = velocity.sum() / 1000
    auxilliary_energy = aux_power * cycle.size / distance #kJ/km

    return np.random.normal(loc=1, scale=.05) * (pa.w.sum() /
        (1000 * distance) + auxilliary_energy) / efficiency / 1000
