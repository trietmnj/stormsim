function [rand_norm_sigmas] = normal_curve_discretizer(number_of_samples, mu, sigma)
    %{
    %% DESCRIPTION
        This function discretizes a normal curve distribution using the
        amount of samples specified. This is used for Response Base
        analysis.
    
    %% INPUTS
        number_of_samples: Number of samples to use. | double | 1 x 1
        mu: Normal distribution mean shape parameter. | double | 1 x 1
        sigma: Normal distirbution standard deviation shape parameter. | double | 1 x 1
    
    %% OUTPUTS
        rand_norm_dist: Discretized normal probability curve standard | double | number_of_samples x 1
                        deviation values.
   
    %% DEV SIGNATURE
       Developed by: Jeff A. Melby, Fabian A. Garcia Moreno ERDC-CHL
    %}
    
    %% DEFINE ADDITIONAL PARAMETERS
    % Define Number Of Replications For Convergence
    number_of_replicates = 1e6;

    %% DISCRETIZE NORMAL CURVE
    pd = makedist('Normal','mu',mu,'sigma',sigma);
    %t = truncate(pd,-3,3);
    t=pd;
    % Create 1e6 Iterations Of "n" Points Randomly Sampled From Normal Curve
    r = random(t,[number_of_replicates number_of_samples]);
    % Sort Each Sample Iteration
    rand_norm_sigmas = sort(r,2);
    % Compute Sample Means (Along Iterations)
    rand_norm_sigmas = nanmean(rand_norm_sigmas,1);
    % Make Normal Curve Symmetrical
        rand_norm_sigmas = nanmean([abs(rand_norm_sigmas(1,1:number_of_samples/2));fliplr(rand_norm_sigmas(1,number_of_samples/2+1:number_of_samples))]);
        rand_norm_sigmas = [-1*rand_norm_sigmas,fliplr(rand_norm_sigmas)];
    % Round Results
    rand_norm_sigmas = round(rand_norm_sigmas,4);
    % Compute Mean
    m0 = mean(rand_norm_sigmas);
    % Compute Standard Deviation
    s0 = std(rand_norm_sigmas);
    % Compute Max
    max_val = max(rand_norm_sigmas);
end