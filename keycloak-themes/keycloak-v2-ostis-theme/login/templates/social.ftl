<#import "template.ftl" as layout>
<@layout.registrationLayout displayInfo=social.displayInfo displayWide=(realm.password && social.providers??); section>
    <#if section = "header">
        ${msg("doLogIn")}
    <#elseif section = "form">
    <div id="kc-social-providers" class="${properties.kcFormSocialAccountSectionClass!}">
        <hr/>
        <h4>${msg("identity-provider-login-label")}</h4>

        <ul class="${properties.kcFormSocialAccountListClass!} <#if social.providers?size gt 3>${properties.kcFormSocialAccountListGridClass!}</#if>">
            <#list social.providers as p>
                <li>
                    <a id="social-${p.alias}" class="${properties.kcFormSocialAccountListButtonClass!} <#if p.iconClasses?has_content>${p.iconClasses}</#if>"
                            type="button" href="${p.loginUrl}">
                        <#if p.alias == "google">
                            <img src="${url.resourcesPath}/img/google.svg" alt="Google" class="kc-social-icon">
                            <span class="${properties.kcFormSocialAccountNameClass!} kc-social-icon-text">${p.displayName!}</span>
                        <#elseif p.iconClasses?has_content>
                            <i class="${properties.kcCommonLogoIdP!} ${p.iconClasses}" aria-hidden="true"></i>
                            <span class="${properties.kcFormSocialAccountNameClass!} kc-social-icon-text">${p.displayName!}</span>
                        <#else>
                            <span class="${properties.kcFormSocialAccountNameClass!} kc-social-icon-text">${p.displayName!}</span>
                        </#if>
                    </a>
                </li>
            </#list>
        </ul>
    </div>
    </#if>
</@layout.registrationLayout>
