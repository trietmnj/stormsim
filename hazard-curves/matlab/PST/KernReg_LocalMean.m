%% KernReg_LocalMean.m
%{
Developed by: E. Ramos-Santiago

Description:
   This function is an adaptation from the original script, to only apply the
    local mean or Nadaraya-Watson estimator (non-parametric regression model) to uni- or multi-variate data,
   following Wand & Jones (1994; Ch5, Sec2). Multivariate regression
   possible to parameters with up to 3 predictors, with order p set to 0
   or 1, only. Normal kernel function is used. Same kernel and bandwidth
   applied to all predictors.

Input:
     x = predictor matrix (one predictor per column)
     y = response parameter (column vector)
     h = bandwidth

Output:
     Y = model prediction (column vector)
     X = predictor grid (same as x)

References:
  Wand, M. P., and Jones, M. C. (1994). Kernel smoothing. Chapman &
    Hall/CRC Monographs on Statistics & Applied Probability, Chapman
    and Hall/CRC press.

History of revisions:
20171206-ERS: developed first draft of function.
20180228-ERS: made revision.
20190109-ERS: expanded algorithm to incorporate multivariate regression using p=0/p=1, only.
20210505-ERS: adapted.
%}
function [X,Y] = KernReg_LocalMean(x,y,H)
[n,k] = size(x); %sample size and dimensionality
X = x;

% setup regression parameters
NN=size(X,1);Y=zeros(NN,1);
Kh =@(H,t,k)H^(-k)*(2*pi)^(k/2)*exp(-0.5*t); %d-variate Normal kernel

%do regression
for i = 1:NN %grid point loop
    t = sum(bsxfun(@minus, X(i,:), x).^2,2)./(H^2);
    Xx = ones(n,1);
    Wx = diag(Kh(H,t,k));
    Y(i) = (Xx'*Wx*Xx)\(Xx'*Wx)*y;
end
end